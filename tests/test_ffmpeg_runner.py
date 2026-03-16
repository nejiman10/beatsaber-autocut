"""Tests for ffmpeg command building and execution."""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from bs_autocut.clip.ffmpeg_runner import (
    build_ffmpeg_command,
    run_clip,
    run_clips,
    run_ffmpeg_command,
)
from bs_autocut.config_loader import FFmpegConfig
from bs_autocut.models import ClipPlan, PlaySession


def test_build_ffmpeg_command_reencode_mode() -> None:
    """Reencode mode should include codec settings and configured extra args."""

    clip_plan = _build_clip_plan()
    ffmpeg_config = FFmpegConfig(
        ffmpeg_bin="ffmpeg-custom",
        mode="reencode",
        video_codec="libx265",
        audio_codec="opus",
        crf=22,
        preset="slow",
        extra_input_args=("-hide_banner",),
        extra_output_args=("-movflags", "+faststart"),
    )

    command = build_ffmpeg_command(clip_plan, ffmpeg_config, overwrite=True)

    assert command == [
        "ffmpeg-custom",
        "-y",
        "-hide_banner",
        "-ss",
        "12.500",
        "-to",
        "34.750",
        "-i",
        str(clip_plan.video_path),
        "-c:v",
        "libx265",
        "-crf",
        "22",
        "-preset",
        "slow",
        "-c:a",
        "opus",
        "-movflags",
        "+faststart",
        str(clip_plan.output_path),
    ]


def test_build_ffmpeg_command_copy_mode() -> None:
    """Copy mode should use stream copy and omit reencode-specific options."""

    clip_plan = _build_clip_plan()
    ffmpeg_config = FFmpegConfig(mode="copy")

    command = build_ffmpeg_command(clip_plan, ffmpeg_config, overwrite=False)

    assert command == [
        "ffmpeg",
        "-n",
        "-ss",
        "12.500",
        "-to",
        "34.750",
        "-i",
        str(clip_plan.video_path),
        "-c",
        "copy",
        str(clip_plan.output_path),
    ]


def test_run_ffmpeg_command_raises_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-zero ffmpeg exit code should be surfaced to callers."""

    def fake_run(command: list[str], check: bool) -> subprocess.CompletedProcess[str]:
        assert check is False
        return subprocess.CompletedProcess(command, returncode=1)

    monkeypatch.setattr("bs_autocut.clip.ffmpeg_runner.subprocess.run", fake_run)

    with pytest.raises(subprocess.CalledProcessError):
        run_ffmpeg_command(["ffmpeg", "-version"])


def test_run_clip_creates_parent_directory_and_executes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Running a clip should create the output directory and execute ffmpeg."""

    output_path = tmp_path / "nested" / "clips" / "clip.mp4"
    clip_plan = _build_clip_plan(output_path=output_path)
    recorded_commands: list[list[str]] = []

    def fake_run(command: list[str]) -> None:
        recorded_commands.append(command)

    monkeypatch.setattr("bs_autocut.clip.ffmpeg_runner.run_ffmpeg_command", fake_run)

    run_clip(
        clip_plan=clip_plan,
        ffmpeg_config=FFmpegConfig(),
        overwrite=False,
        dry_run=False,
    )

    assert output_path.parent.is_dir()
    assert recorded_commands == [
        [
            "ffmpeg",
            "-n",
            "-ss",
            "12.500",
            "-to",
            "34.750",
            "-i",
            str(clip_plan.video_path),
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-preset",
            "fast",
            "-c:a",
            "aac",
            str(output_path),
        ]
    ]


def test_run_clip_skips_execution_in_dry_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Dry-run mode should not create directories or execute ffmpeg."""

    output_path = tmp_path / "nested" / "clips" / "clip.mp4"
    clip_plan = _build_clip_plan(output_path=output_path)
    executed = False

    def fake_run(command: list[str]) -> None:
        nonlocal executed
        executed = True

    monkeypatch.setattr("bs_autocut.clip.ffmpeg_runner.run_ffmpeg_command", fake_run)

    run_clip(
        clip_plan=clip_plan,
        ffmpeg_config=FFmpegConfig(),
        overwrite=False,
        dry_run=True,
    )

    assert executed is False
    assert output_path.parent.exists() is False


def test_run_clips_processes_each_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Batch execution should forward each plan to run_clip."""

    clip_plans = [
        _build_clip_plan(output_path=tmp_path / "one.mp4"),
        _build_clip_plan(output_path=tmp_path / "two.mp4"),
    ]
    seen_paths: list[Path] = []

    def fake_run_clip(
        clip_plan: ClipPlan,
        ffmpeg_config: FFmpegConfig,
        overwrite: bool,
        dry_run: bool,
    ) -> None:
        assert ffmpeg_config.mode == "copy"
        assert overwrite is True
        assert dry_run is False
        seen_paths.append(clip_plan.output_path)

    monkeypatch.setattr("bs_autocut.clip.ffmpeg_runner.run_clip", fake_run_clip)

    run_clips(
        clip_plans=clip_plans,
        ffmpeg_config=FFmpegConfig(mode="copy"),
        overwrite=True,
        dry_run=False,
    )

    assert seen_paths == [tmp_path / "one.mp4", tmp_path / "two.mp4"]


def _build_clip_plan(output_path: Path | None = None) -> ClipPlan:
    """Create a representative clip plan for ffmpeg runner tests."""

    session = PlaySession(
        start_time=1710000123,
        end_time=1710000223,
        start=1710000130,
        menu_time=1710000250,
        song_hash="abc12345deadbeef",
        song_name="Song",
        difficulty="Expert",
        rank="A",
        score=100,
        cleared="true",
    )
    return ClipPlan(
        video_path=Path("/videos/input.mp4"),
        start_sec=12.5,
        end_sec=34.75,
        output_path=output_path or Path("/clips/output.mp4"),
        session=session,
    )
