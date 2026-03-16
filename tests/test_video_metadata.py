"""Tests for ffprobe-backed video metadata helpers."""

from __future__ import annotations

from datetime import datetime
import os
from pathlib import Path
import subprocess
from unittest.mock import Mock

import pytest

from bs_autocut.video.metadata import (
    _parse_obs_timestamp_from_filename,
    probe_video_file,
    probe_video_files,
)


def test_probe_video_file_uses_creation_time_when_available(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Metadata probing should prefer ffprobe creation_time over file mtime."""

    video_path = tmp_path / "recording.mp4"
    video_path.write_text("")
    video_path.touch()

    completed_process = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout='{"format":{"duration":"12.5","tags":{"creation_time":"2024-01-02T03:04:05Z"}}}',
        stderr="",
    )
    monkeypatch.setattr(subprocess, "run", Mock(return_value=completed_process))

    video_file = probe_video_file(video_path, "ffprobe")

    assert video_file.path == video_path
    assert video_file.duration == 12.5
    assert video_file.start_time == 1704164645.0


def test_probe_video_file_falls_back_to_mtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Metadata probing should fall back to file mtime when no better timestamp exists."""

    video_path = tmp_path / "recording.mp4"
    video_path.write_text("")

    mtime = 1700000000.5
    os.utime(video_path, (mtime, mtime))
    completed_process = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout='{"format":{"duration":"99.0"}}',
        stderr="",
    )
    monkeypatch.setattr(subprocess, "run", Mock(return_value=completed_process))

    video_file = probe_video_file(video_path, "ffprobe")

    assert video_file.start_time == mtime
    assert video_file.duration == 99.0


def test_parse_obs_timestamp_from_filename_returns_datetime_for_matching_stem() -> None:
    """OBS-style filenames should be parsed into local datetimes."""

    parsed = _parse_obs_timestamp_from_filename(Path("2026-03-16_22-11-14.mkv"))

    assert parsed == datetime(2026, 3, 16, 22, 11, 14)


def test_parse_obs_timestamp_from_filename_returns_none_for_non_matching_stem() -> None:
    """Non-OBS filenames should not produce a parsed timestamp."""

    parsed = _parse_obs_timestamp_from_filename(Path("recording.mkv"))

    assert parsed is None


def test_probe_video_file_prefers_filename_timestamp_over_mtime_when_creation_time_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Filename timestamps should win over mtime when ffprobe lacks creation_time."""

    video_path = tmp_path / "2026-03-16_22-11-14.mkv"
    video_path.write_text("")

    mtime = 1800000000.5
    os.utime(video_path, (mtime, mtime))
    completed_process = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout='{"format":{"duration":"99.0"}}',
        stderr="",
    )
    monkeypatch.setattr(subprocess, "run", Mock(return_value=completed_process))

    video_file = probe_video_file(video_path, "ffprobe")

    assert video_file.start_time == datetime(2026, 3, 16, 22, 11, 14).timestamp()
    assert video_file.start_time != mtime
    assert video_file.duration == 99.0


def test_probe_video_files_sorts_by_start_time(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Batch probing should return VideoFile objects sorted by start_time."""

    later_path = tmp_path / "later.mp4"
    earlier_path = tmp_path / "earlier.mp4"
    later_path.write_text("")
    earlier_path.write_text("")

    outputs = {
        str(later_path): subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout='{"format":{"duration":"10","tags":{"creation_time":"2024-01-02T00:00:10Z"}}}',
            stderr="",
        ),
        str(earlier_path): subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout='{"format":{"duration":"10","tags":{"creation_time":"2024-01-02T00:00:05Z"}}}',
            stderr="",
        ),
    }

    def fake_run(command: list[str], capture_output: bool, text: bool, check: bool) -> subprocess.CompletedProcess[str]:
        return outputs[command[-1]]

    monkeypatch.setattr(subprocess, "run", fake_run)

    video_files = probe_video_files([later_path, earlier_path], "ffprobe")

    assert [video_file.path for video_file in video_files] == [earlier_path, later_path]
