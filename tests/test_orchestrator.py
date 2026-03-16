"""Tests for pipeline orchestration."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from bs_autocut.config_loader import (
    AppConfig,
    CutConfig,
    FFmpegConfig,
    FilterConfig,
    OrganizeConfig,
    OutputConfig,
    PathsConfig,
    RunConfig,
    VideoConfig,
)
from bs_autocut.models import ClipPlan, PlaySession, VideoFile
from bs_autocut.orchestrator import run_pipeline


def test_run_pipeline_builds_final_output_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pipeline should replace planner placeholders with configured filenames."""

    config = AppConfig(
        paths=PathsConfig(
            db=tmp_path / "beatsaber.db",
            videos=tmp_path / "videos",
            output=tmp_path / "clips",
        ),
        cut=CutConfig(mode="song", pre_roll=3.0, post_roll=2.0),
        video=VideoConfig(extensions=("mp4",)),
        output=OutputConfig(
            format="mp4",
            filename_template="{song} [{difficulty}] {rank} {score}",
        ),
        organize=OrganizeConfig(enabled=True, path_template="{song}/{difficulty}"),
        ffmpeg=FFmpegConfig(ffprobe_bin="ffprobe"),
        run=RunConfig(dry_run=False, overwrite=False),
    )
    recorded_calls: list[tuple[list[ClipPlan], FFmpegConfig, bool, bool]] = []
    session = PlaySession(
        start_time=1710000123,
        end_time=1710000223,
        start=1710000130,
        menu_time=1710000250,
        song_hash="abc12345deadbeef",
        song_name="Idol",
        difficulty="ExpertPlus",
        rank="SS",
        score=1234567,
        cleared="true",
    )
    video = VideoFile(path=tmp_path / "videos" / "recording.mp4", start_time=1710000000.0, duration=600.0)
    placeholder_plan = ClipPlan(
        video_path=video.path,
        start_sec=10.0,
        end_sec=20.0,
        output_path=tmp_path / "clips" / "placeholder",
        session=session,
    )

    monkeypatch.setattr("bs_autocut.orchestrator.load_config", lambda _: config)
    monkeypatch.setattr("bs_autocut.orchestrator.read_sessions_from_db", lambda _: [session])
    monkeypatch.setattr("bs_autocut.orchestrator.scan_video_files", lambda *_: [video.path])
    monkeypatch.setattr("bs_autocut.orchestrator.probe_video_files", lambda *_: [video])
    monkeypatch.setattr("bs_autocut.orchestrator.build_clip_plans", lambda **_: [placeholder_plan])
    monkeypatch.setattr(
        "bs_autocut.orchestrator.run_clips",
        lambda clip_plans, ffmpeg_config, overwrite, dry_run: recorded_calls.append(
            (clip_plans, ffmpeg_config, overwrite, dry_run)
        ),
    )

    clip_plans = run_pipeline(tmp_path / "config.toml")

    expected_plans = [
        ClipPlan(
            video_path=video.path,
            start_sec=10.0,
            end_sec=20.0,
            output_path=tmp_path
            / "clips"
            / "Idol"
            / "ExpertPlus"
            / "Idol [ExpertPlus] SS 1234567__1710000123_abc12345.mp4",
            session=session,
        )
    ]
    assert clip_plans == expected_plans
    assert recorded_calls == [(expected_plans, config.ffmpeg, False, False)]

def test_run_pipeline_logs_plans_and_skips_execution_in_dry_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Dry-run mode should log the generated plans."""

    config = AppConfig(
        paths=PathsConfig(
            db=tmp_path / "beatsaber.db",
            videos=tmp_path / "videos",
            output=tmp_path / "clips",
        ),
        video=VideoConfig(extensions=("mp4",)),
        output=OutputConfig(format="mp4", filename_template="{song}"),
        organize=OrganizeConfig(enabled=False, path_template="{song}"),
        ffmpeg=FFmpegConfig(ffprobe_bin="ffprobe"),
        run=RunConfig(dry_run=True, overwrite=False),
    )
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
    plan = ClipPlan(
        video_path=tmp_path / "videos" / "recording.mp4",
        start_sec=1.0,
        end_sec=2.0,
        output_path=tmp_path / "clips" / "placeholder",
        session=session,
    )
    recorded_calls: list[tuple[list[ClipPlan], FFmpegConfig, bool, bool]] = []

    monkeypatch.setattr("bs_autocut.orchestrator.load_config", lambda _: config)
    monkeypatch.setattr("bs_autocut.orchestrator.read_sessions_from_db", lambda _: [session])
    monkeypatch.setattr("bs_autocut.orchestrator.scan_video_files", lambda *_: [])
    monkeypatch.setattr("bs_autocut.orchestrator.probe_video_files", lambda *_: [])
    monkeypatch.setattr("bs_autocut.orchestrator.build_clip_plans", lambda **_: [plan])
    monkeypatch.setattr(
        "bs_autocut.orchestrator.run_clips",
        lambda clip_plans, ffmpeg_config, overwrite, dry_run: recorded_calls.append(
            (clip_plans, ffmpeg_config, overwrite, dry_run)
        ),
    )

    caplog.set_level(logging.INFO)

    clip_plans = run_pipeline(tmp_path / "config.toml")

    assert "Dry run enabled. Planned 1 clips:" in caplog.text
    assert "Song__1710000123_abc12345.mp4" in caplog.text
    assert recorded_calls == [(clip_plans, config.ffmpeg, False, True)]


def test_run_pipeline_executes_clips_and_logs_completion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Non-dry-run mode should hand final plans to the ffmpeg runner."""

    config = AppConfig(
        paths=PathsConfig(
            db=tmp_path / "beatsaber.db",
            videos=tmp_path / "videos",
            output=tmp_path / "clips",
        ),
        video=VideoConfig(extensions=("mp4",)),
        output=OutputConfig(format="mp4", filename_template="{song}"),
        organize=OrganizeConfig(enabled=False, path_template="{song}"),
        ffmpeg=FFmpegConfig(ffmpeg_bin="ffmpeg-custom", ffprobe_bin="ffprobe", mode="copy"),
        run=RunConfig(dry_run=False, overwrite=True),
    )
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
    plan = ClipPlan(
        video_path=tmp_path / "videos" / "recording.mp4",
        start_sec=1.0,
        end_sec=2.0,
        output_path=tmp_path / "clips" / "placeholder",
        session=session,
    )
    recorded_calls: list[tuple[list[ClipPlan], FFmpegConfig, bool, bool]] = []

    monkeypatch.setattr("bs_autocut.orchestrator.load_config", lambda _: config)
    monkeypatch.setattr("bs_autocut.orchestrator.read_sessions_from_db", lambda _: [session])
    monkeypatch.setattr("bs_autocut.orchestrator.scan_video_files", lambda *_: [])
    monkeypatch.setattr("bs_autocut.orchestrator.probe_video_files", lambda *_: [])
    monkeypatch.setattr("bs_autocut.orchestrator.build_clip_plans", lambda **_: [plan])
    monkeypatch.setattr(
        "bs_autocut.orchestrator.run_clips",
        lambda clip_plans, ffmpeg_config, overwrite, dry_run: recorded_calls.append(
            (clip_plans, ffmpeg_config, overwrite, dry_run)
        ),
    )

    caplog.set_level(logging.INFO)

    clip_plans = run_pipeline(tmp_path / "config.toml")

    assert "Generating 1 clips with ffmpeg-custom" in caplog.text
    assert "Completed clip generation" in caplog.text
    assert recorded_calls == [(clip_plans, config.ffmpeg, True, False)]


def test_run_pipeline_merges_start_time_override_with_config_filter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pipeline should merge runtime start-time overrides with config filters."""

    config = AppConfig(
        paths=PathsConfig(
            db=tmp_path / "beatsaber.db",
            videos=tmp_path / "videos",
            output=tmp_path / "clips",
        ),
        filter=FilterConfig(include_start_times=(1710000123,)),
        video=VideoConfig(extensions=("mp4",)),
        output=OutputConfig(format="mp4", filename_template="{song}"),
        organize=OrganizeConfig(enabled=False, path_template="{song}"),
        ffmpeg=FFmpegConfig(ffprobe_bin="ffprobe"),
        run=RunConfig(dry_run=True, overwrite=False),
    )
    matched_session = PlaySession(
        start_time=1710000456,
        end_time=1710000556,
        start=1710000460,
        menu_time=1710000560,
        song_hash="override1234567890",
        song_name="Override Song",
        difficulty="Expert",
        rank="S",
        score=1000,
        cleared="true",
    )
    config_session = PlaySession(
        start_time=1710000123,
        end_time=1710000223,
        start=1710000130,
        menu_time=1710000230,
        song_hash="config1234567890ab",
        song_name="Config Song",
        difficulty="Hard",
        rank="A",
        score=900,
        cleared="true",
    )
    filtered_sessions: list[PlaySession] = []

    monkeypatch.setattr("bs_autocut.orchestrator.load_config", lambda _: config)
    monkeypatch.setattr(
        "bs_autocut.orchestrator.read_sessions_from_db",
        lambda _: [matched_session, config_session],
    )
    monkeypatch.setattr("bs_autocut.orchestrator.scan_video_files", lambda *_: [])
    monkeypatch.setattr("bs_autocut.orchestrator.probe_video_files", lambda *_: [])
    monkeypatch.setattr(
        "bs_autocut.orchestrator.build_clip_plans",
        lambda **kwargs: filtered_sessions.extend(kwargs["sessions"]) or [],
    )
    monkeypatch.setattr("bs_autocut.orchestrator.run_clips", lambda **_: None)

    run_pipeline(
        tmp_path / "config.toml",
        include_start_times_override=[1710000456],
    )

    assert filtered_sessions == [matched_session, config_session]
