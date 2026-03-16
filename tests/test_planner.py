"""Tests for clip planning helpers."""

from __future__ import annotations

from pathlib import Path

from bs_autocut.clip.planner import build_clip_plan
from bs_autocut.models import PlaySession, VideoFile


def test_build_clip_plan_applies_zero_time_offset() -> None:
    """Zero offset should preserve the resolved session timing."""

    plan = build_clip_plan(
        session=_build_session(),
        video=_build_video(),
        cut_mode="song",
        pre_roll=5.0,
        post_roll=2.0,
        time_offset=0.0,
        output_path=Path("clip.mp4"),
    )

    assert plan is not None
    assert plan.start_sec == 15.0
    assert plan.end_sec == 42.0


def test_build_clip_plan_applies_positive_time_offset() -> None:
    """Positive offsets should shift the clip later."""

    plan = build_clip_plan(
        session=_build_session(),
        video=_build_video(),
        cut_mode="song",
        pre_roll=5.0,
        post_roll=2.0,
        time_offset=3.5,
        output_path=Path("clip.mp4"),
    )

    assert plan is not None
    assert plan.start_sec == 18.5
    assert plan.end_sec == 45.5


def test_build_clip_plan_applies_negative_time_offset() -> None:
    """Negative offsets should shift the clip earlier."""

    plan = build_clip_plan(
        session=_build_session(),
        video=_build_video(),
        cut_mode="song",
        pre_roll=5.0,
        post_roll=2.0,
        time_offset=-4.0,
        output_path=Path("clip.mp4"),
    )

    assert plan is not None
    assert plan.start_sec == 11.0
    assert plan.end_sec == 38.0


def _build_session() -> PlaySession:
    return PlaySession(
        start_time=1_700_000_020,
        end_time=1_700_000_040,
        start=1_700_000_020,
        menu_time=1_700_000_045,
        song_hash="abc12345deadbeef",
        song_name="Song",
        difficulty="Expert",
        rank="S",
        score=1234,
        cleared="true",
    )


def _build_video() -> VideoFile:
    return VideoFile(
        path=Path("recording.mp4"),
        start_time=1_700_000_000.0,
        duration=120.0,
    )
