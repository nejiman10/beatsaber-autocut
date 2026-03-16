"""Pipeline orchestration for Beat Saber auto clip planning."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
import logging
from pathlib import Path

from bs_autocut.clip.ffmpeg_runner import run_clips
from bs_autocut.clip.planner import build_clip_plans
from bs_autocut.config_loader import AppConfig, FilterConfig, load_config
from bs_autocut.db.reader import read_sessions_from_db
from bs_autocut.models import ClipPlan, PlaySession
from bs_autocut.output.filename_builder import build_filename, sanitize_filename
from bs_autocut.session.filter import filter_sessions
from bs_autocut.video.metadata import probe_video_files
from bs_autocut.video.scanner import scan_video_files

LOGGER = logging.getLogger(__name__)
TIMESTAMP_MS_THRESHOLD = 1e12


def run_pipeline(
    config_path: Path,
    include_start_times_override: list[int] | None = None,
) -> list[ClipPlan]:
    """Run the clip planning pipeline."""

    LOGGER.info("Loading configuration from %s", config_path)
    config = load_config(config_path)

    LOGGER.info("Reading play sessions from %s", config.paths.db)
    sessions = read_sessions_from_db(config.paths.db)
    LOGGER.info("Loaded %d play sessions", len(sessions))

    LOGGER.info("Filtering play sessions")
    session_filter = _resolve_filter_config(config.filter, include_start_times_override)
    sessions = filter_sessions(sessions, session_filter)
    LOGGER.info("Retained %d play sessions after filtering", len(sessions))

    LOGGER.info("Scanning video files in %s", config.paths.videos)
    video_paths = scan_video_files(config.paths.videos, list(config.video.extensions))
    LOGGER.info("Found %d video files", len(video_paths))

    LOGGER.info("Probing video metadata with %s", config.ffmpeg.ffprobe_bin)
    videos = probe_video_files(video_paths, config.ffmpeg.ffprobe_bin)
    LOGGER.info("Probed %d video files", len(videos))

    LOGGER.info("Building clip plans using cut mode %s", config.cut.mode)
    clip_plans = build_clip_plans(
        sessions=sessions,
        videos=videos,
        cut_mode=config.cut.mode,
        pre_roll=config.cut.pre_roll,
        post_roll=config.cut.post_roll,
        time_offset=config.cut.time_offset,
        output_dir=config.paths.output,
    )
    LOGGER.info("Built %d clip plans", len(clip_plans))

    clip_plans = [_apply_output_path(plan, config) for plan in clip_plans]

    if config.run.dry_run:
        _log_dry_run_plans(clip_plans)
    else:
        LOGGER.info("Generating %d clips with %s", len(clip_plans), config.ffmpeg.ffmpeg_bin)

    run_clips(
        clip_plans=clip_plans,
        ffmpeg_config=config.ffmpeg,
        overwrite=config.run.overwrite,
        dry_run=config.run.dry_run,
    )

    if not config.run.dry_run:
        LOGGER.info("Completed clip generation")

    return clip_plans


def _resolve_filter_config(
    filter_config: FilterConfig,
    include_start_times_override: list[int] | None,
) -> FilterConfig:
    """Merge runtime start-time overrides into the filter config."""

    if include_start_times_override is None:
        return filter_config

    return replace(
        filter_config,
        include_start_times=filter_config.include_start_times + tuple(include_start_times_override),
    )


def _apply_output_path(plan: ClipPlan, config: AppConfig) -> ClipPlan:
    """Replace the planner output path with the configured final path."""

    output_path = _build_output_path(plan.session, config)
    return replace(plan, output_path=output_path)


def _build_output_path(session: PlaySession, config: AppConfig) -> Path:
    """Build the final output path for a planned clip."""

    filename = build_filename(
        session=session,
        template=config.output.filename_template,
        ext=config.output.format,
    )

    if not config.organize.enabled:
        return config.paths.output / filename

    output_dir = _build_organized_directory(session, config.organize.path_template)
    return config.paths.output / output_dir / filename


def _build_organized_directory(session: PlaySession, template: str) -> Path:
    """Build a sanitized relative directory path from an organization template."""

    rendered = template.format(**_build_template_values(session)).strip()
    normalized = rendered.replace("\\", "/")
    parts = [
        sanitized_part
        for raw_part in normalized.split("/")
        if raw_part.strip()
        for sanitized_part in [sanitize_filename(raw_part).strip(" .")]
        if sanitized_part
    ]

    if not parts:
        return Path()
    return Path(*parts)


def _build_template_values(session: PlaySession) -> dict[str, str]:
    """Build shared filename and directory template values."""

    start_datetime = _datetime_from_timestamp(session.start_time)
    return {
        "song": session.song_name,
        "difficulty": session.difficulty,
        "rank": session.rank,
        "score": str(session.score),
        "hash": session.song_hash,
        "start_time": str(session.start_time),
        "date": start_datetime.strftime("%Y-%m-%d"),
        "time": start_datetime.strftime("%H-%M-%S"),
    }


def _datetime_from_timestamp(timestamp: int) -> datetime:
    """Convert a recorded session timestamp to local time."""

    normalized = float(timestamp)
    if normalized > TIMESTAMP_MS_THRESHOLD:
        normalized /= 1000.0
    return datetime.fromtimestamp(normalized)


def _log_dry_run_plans(clip_plans: list[ClipPlan]) -> None:
    """Log the planned clips without executing any output actions."""

    LOGGER.info("Dry run enabled. Planned %d clips:", len(clip_plans))
    for plan in clip_plans:
        LOGGER.info(
            "clip video=%s start=%.3f end=%.3f output=%s",
            plan.video_path,
            plan.start_sec,
            plan.end_sec,
            plan.output_path,
        )
