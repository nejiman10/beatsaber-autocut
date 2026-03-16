"""FFmpeg command construction and execution for planned clips."""

from __future__ import annotations

from pathlib import Path
import subprocess

from bs_autocut.config_loader import FFmpegConfig
from bs_autocut.models import ClipPlan


def build_ffmpeg_command(
    clip_plan: ClipPlan,
    ffmpeg_config: FFmpegConfig,
    overwrite: bool,
) -> list[str]:
    """Build the ffmpeg command for a single clip plan."""

    command: list[str] = [ffmpeg_config.ffmpeg_bin]
    command.append("-y" if overwrite else "-n")
    command.extend(ffmpeg_config.extra_input_args)
    command.extend(
        [
            "-ss",
            _format_time_arg(clip_plan.start_sec),
            "-to",
            _format_time_arg(clip_plan.end_sec),
            "-i",
            str(clip_plan.video_path),
        ]
    )

    if ffmpeg_config.mode == "reencode":
        command.extend(
            [
                "-c:v",
                ffmpeg_config.video_codec,
                "-crf",
                str(ffmpeg_config.crf),
                "-preset",
                ffmpeg_config.preset,
                "-c:a",
                ffmpeg_config.audio_codec,
            ]
        )
    elif ffmpeg_config.mode == "copy":
        command.extend(["-c", "copy"])
    else:
        raise ValueError(f"Unsupported ffmpeg mode: {ffmpeg_config.mode!r}.")

    command.extend(ffmpeg_config.extra_output_args)
    command.append(str(clip_plan.output_path))
    return command


def run_ffmpeg_command(command: list[str]) -> None:
    """Execute a prebuilt ffmpeg command and raise on failure."""

    completed_process = subprocess.run(command, check=False)
    if completed_process.returncode != 0:
        raise subprocess.CalledProcessError(completed_process.returncode, command)


def run_clip(
    clip_plan: ClipPlan,
    ffmpeg_config: FFmpegConfig,
    overwrite: bool,
    dry_run: bool,
) -> None:
    """Generate one clip from a clip plan unless dry-run mode is enabled."""

    command = build_ffmpeg_command(
        clip_plan=clip_plan,
        ffmpeg_config=ffmpeg_config,
        overwrite=overwrite,
    )

    if dry_run:
        return

    _ensure_parent_directory(clip_plan.output_path)
    run_ffmpeg_command(command)


def run_clips(
    clip_plans: list[ClipPlan],
    ffmpeg_config: FFmpegConfig,
    overwrite: bool,
    dry_run: bool,
) -> None:
    """Generate clips for every provided clip plan."""

    for clip_plan in clip_plans:
        run_clip(
            clip_plan=clip_plan,
            ffmpeg_config=ffmpeg_config,
            overwrite=overwrite,
            dry_run=dry_run,
        )


def _ensure_parent_directory(output_path: Path) -> None:
    """Create the output directory for a clip if it does not already exist."""

    output_path.parent.mkdir(parents=True, exist_ok=True)


def _format_time_arg(value: float) -> str:
    """Format ffmpeg timestamp arguments using fixed decimal precision."""

    return f"{value:.3f}"
