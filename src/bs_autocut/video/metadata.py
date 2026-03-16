"""ffprobe-based metadata readers for source video files."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import subprocess
from typing import Any

from bs_autocut.models import VideoFile


def probe_video_file(path: Path, ffprobe_bin: str) -> VideoFile:
    """Read metadata for a single video file and build a VideoFile object."""

    probe_data = _run_ffprobe(path, ffprobe_bin)
    duration = _read_duration(probe_data, path)
    start_time = _read_start_time(probe_data, path)
    return VideoFile(path=path, start_time=start_time, duration=duration)


def probe_video_files(paths: list[Path], ffprobe_bin: str) -> list[VideoFile]:
    """Probe multiple video files and return them sorted by recording start time."""

    video_files = [probe_video_file(path, ffprobe_bin) for path in paths]
    return sorted(video_files, key=_video_sort_key)


def _run_ffprobe(path: Path, ffprobe_bin: str) -> dict[str, Any]:
    """Execute ffprobe and parse its JSON output."""

    command = _build_ffprobe_command(path, ffprobe_bin)
    completed_process = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    if completed_process.returncode != 0:
        error_output = completed_process.stderr.strip() or completed_process.stdout.strip()
        raise RuntimeError(f"ffprobe failed for {path}: {error_output}")

    stdout = completed_process.stdout.strip()
    if not stdout:
        raise ValueError(f"ffprobe returned empty output for {path}.")

    try:
        raw_data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"ffprobe returned invalid JSON for {path}.") from exc

    if not isinstance(raw_data, dict):
        raise ValueError(f"ffprobe JSON root must be an object for {path}.")
    return raw_data


def _build_ffprobe_command(path: Path, ffprobe_bin: str) -> list[str]:
    """Build the ffprobe command used to collect duration and creation time."""

    return [
        ffprobe_bin,
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_entries",
        "format=duration:format_tags=creation_time:stream_tags=creation_time",
        str(path),
    ]


def _read_duration(probe_data: dict[str, Any], path: Path) -> float:
    """Extract and validate the video duration from ffprobe output."""

    format_data = _read_mapping(probe_data, "format", path)
    raw_duration = format_data.get("duration")
    if isinstance(raw_duration, bool) or raw_duration is None:
        raise ValueError(f"Missing ffprobe duration for {path}.")

    try:
        duration = float(raw_duration)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid ffprobe duration for {path}: {raw_duration!r}.") from exc

    if duration <= 0.0:
        raise ValueError(f"Video duration must be positive for {path}.")
    return duration


def _read_start_time(probe_data: dict[str, Any], path: Path) -> float:
    """Resolve the recording start time using metadata, filename, or filesystem mtime."""

    creation_time = _find_creation_time(probe_data)
    if creation_time is not None:
        parsed_creation_time = _parse_creation_time(creation_time, path)
        return parsed_creation_time.timestamp()

    filename_datetime = _parse_obs_timestamp_from_filename(path)
    if filename_datetime is not None:
        return filename_datetime.timestamp()

    return _read_file_mtime(path)


def _parse_obs_timestamp_from_filename(path: Path) -> datetime | None:
    """Parse an OBS-style recording timestamp from a file stem when present."""

    try:
        return datetime.strptime(path.stem, "%Y-%m-%d_%H-%M-%S")
    except ValueError:
        return None


def _find_creation_time(probe_data: dict[str, Any]) -> str | None:
    """Find a creation_time tag in the format section or any stream section."""

    format_data = probe_data.get("format")
    if isinstance(format_data, dict):
        format_tags = format_data.get("tags")
        creation_time = _read_creation_time_from_tags(format_tags)
        if creation_time is not None:
            return creation_time

    streams = probe_data.get("streams")
    if not isinstance(streams, list):
        return None

    for stream in streams:
        if not isinstance(stream, dict):
            continue
        creation_time = _read_creation_time_from_tags(stream.get("tags"))
        if creation_time is not None:
            return creation_time

    return None


def _read_creation_time_from_tags(tags: Any) -> str | None:
    """Read a creation_time tag from a tag mapping when present."""

    if not isinstance(tags, dict):
        return None

    value = tags.get("creation_time")
    if not isinstance(value, str):
        return None

    stripped_value = value.strip()
    if not stripped_value:
        return None
    return stripped_value


def _parse_creation_time(value: str, path: Path) -> datetime:
    """Parse an ffprobe creation_time value into a datetime."""

    normalized_value = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized_value)
    except ValueError as exc:
        raise ValueError(f"Invalid ffprobe creation_time for {path}: {value!r}.") from exc


def _read_mapping(data: dict[str, Any], key: str, path: Path) -> dict[str, Any]:
    """Read a mapping field from parsed ffprobe output."""

    value = data.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"ffprobe output missing '{key}' object for {path}.")
    return value


def _read_file_mtime(path: Path) -> float:
    """Read the filesystem modification time for a path."""

    return path.stat().st_mtime


def _video_sort_key(video_file: VideoFile) -> tuple[float, str]:
    """Sort probed videos by start time and then path for deterministic output."""

    return video_file.start_time, str(video_file.path)
