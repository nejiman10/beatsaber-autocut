"""Clip planning helpers for converting sessions and videos into ClipPlan objects."""

from __future__ import annotations

from pathlib import Path

from bs_autocut.models import ClipPlan, PlaySession, VideoFile

TIMESTAMP_MS_THRESHOLD = 1e12
SUPPORTED_CUT_MODES = {"song", "play", "with_result"}


def normalize_timestamp(value: int | None) -> float | None:
    """Normalize a timestamp to seconds, handling millisecond inputs."""

    if value is None:
        return None

    normalized = float(value)
    if normalized > TIMESTAMP_MS_THRESHOLD:
        normalized /= 1000.0
    return normalized


def resolve_session_range(
    session: PlaySession,
    cut_mode: str,
) -> tuple[float, float] | None:
    """Resolve the source timestamps for a session based on the selected cut mode."""

    if cut_mode == "song":
        start_time = normalize_timestamp(session.start)
        end_time = normalize_timestamp(session.end_time)
    elif cut_mode == "play":
        start_time = normalize_timestamp(session.start_time)
        end_time = normalize_timestamp(session.end_time)
    elif cut_mode == "with_result":
        start_time = normalize_timestamp(session.start)
        end_time = normalize_timestamp(session.menu_time)
    else:
        raise ValueError(
            f"Unsupported cut mode: {cut_mode!r}. Expected one of {sorted(SUPPORTED_CUT_MODES)}."
        )

    if start_time is None or end_time is None:
        return None
    if end_time <= start_time:
        return None

    return start_time, end_time


def find_matching_video(
    session_start: float,
    videos: list[VideoFile],
) -> VideoFile | None:
    """Find the video whose time range contains the session start timestamp."""

    for video in videos:
        video_end = video.start_time + video.duration
        if video.start_time <= session_start <= video_end:
            return video
    return None


def build_clip_plan(
    session: PlaySession,
    video: VideoFile,
    cut_mode: str,
    pre_roll: float,
    post_roll: float,
    time_offset: float,
    output_path: Path,
) -> ClipPlan | None:
    """Build a single ClipPlan for a session matched to a specific video."""

    session_range = resolve_session_range(session, cut_mode)
    if session_range is None:
        return None

    session_start, session_end = session_range
    adjusted_session_start = session_start + time_offset
    adjusted_session_end = session_end + time_offset

    start_sec = (adjusted_session_start - video.start_time) - pre_roll
    end_sec = (adjusted_session_end - video.start_time) + post_roll

    clamped_start = _clamp_time(start_sec, video.duration)
    clamped_end = _clamp_time(end_sec, video.duration)

    if clamped_end <= clamped_start:
        return None

    return ClipPlan(
        video_path=video.path,
        start_sec=clamped_start,
        end_sec=clamped_end,
        output_path=output_path,
        session=session,
    )


def build_clip_plans(
    sessions: list[PlaySession],
    videos: list[VideoFile],
    cut_mode: str,
    pre_roll: float,
    post_roll: float,
    time_offset: float,
    output_dir: Path,
) -> list[ClipPlan]:
    """Build clip plans for every session that can be resolved and matched to a video."""

    clip_plans: list[ClipPlan] = []

    for session in sessions:
        session_start_time = normalize_timestamp(session.start_time)
        if session_start_time is None:
            continue

        video = find_matching_video(session_start_time, videos)
        if video is None:
            continue

        output_path = _build_output_path(output_dir, session)
        clip_plan = build_clip_plan(
            session=session,
            video=video,
            cut_mode=cut_mode,
            pre_roll=pre_roll,
            post_roll=post_roll,
            time_offset=time_offset,
            output_path=output_path,
        )
        if clip_plan is not None:
            clip_plans.append(clip_plan)

    return clip_plans


def _clamp_time(value: float, duration: float) -> float:
    """Clamp a clip offset to the inclusive bounds of a video duration."""

    if value < 0.0:
        return 0.0
    if value > duration:
        return duration
    return value


def _build_output_path(output_dir: Path, session: PlaySession) -> Path:
    """Build the default output path for a planned clip."""

    return output_dir / f"{session.start_time}_{session.song_hash[:8]}"
