"""Tests for interactive CLI session selection helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from bs_autocut.cli_select import (
    format_session_row,
    parse_selection,
    prompt_start_time_overrides,
    recent_sessions,
    selected_start_times_from_input,
)
from bs_autocut.config_loader import AppConfig, FilterConfig, PathsConfig, SelectConfig
from bs_autocut.models import PlaySession


def test_parse_selection_accepts_single_index() -> None:
    """Single-number selections should parse to one 1-based index."""

    assert parse_selection("3", max_index=5) == [3]


def test_parse_selection_accepts_multiple_indices() -> None:
    """Comma-separated selections should preserve the entered order."""

    assert parse_selection("1, 4,5", max_index=5) == [1, 4, 5]


def test_parse_selection_rejects_invalid_index() -> None:
    """Out-of-range selections should fail clearly."""

    with pytest.raises(ValueError, match="selection 4 is out of range"):
        parse_selection("4", max_index=3)


def test_selected_start_times_from_input_uses_selected_rows() -> None:
    """Selected row numbers should map to the corresponding session start times."""

    sessions = [
        _build_session(start_time=1773666727739),
        _build_session(start_time=1773666732475),
        _build_session(start_time=1773666843706),
    ]

    selected_start_times = selected_start_times_from_input("1,3", sessions)

    assert selected_start_times == [1773666727739, 1773666843706]


def test_recent_sessions_applies_recent_limit() -> None:
    """The selector should display only the most recent configured sessions."""

    sessions = [
        _build_session(start_time=100),
        _build_session(start_time=300),
        _build_session(start_time=200),
    ]

    limited_sessions = recent_sessions(sessions, recent_limit=2)

    assert [session.start_time for session in limited_sessions] == [300, 200]


def test_format_session_row_includes_start_time() -> None:
    """Displayed rows should include the unique start_time identifier."""

    row = format_session_row(2, _build_session(start_time=1773666732475))

    assert row == "[2] Song | Expert | S | finished | 1773666732475"


def test_prompt_start_time_overrides_cancels_on_empty_input(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """Empty input should cancel selection without returning overrides."""

    config = AppConfig(
        paths=PathsConfig(
            db=tmp_path / "beatsaber.db",
            videos=tmp_path / "videos",
            output=tmp_path / "clips",
        ),
        filter=FilterConfig(),
        select=SelectConfig(recent_limit=20),
    )
    monkeypatch.setattr("bs_autocut.cli_select.load_config", lambda _: config)
    monkeypatch.setattr(
        "bs_autocut.cli_select.read_sessions_from_db",
        lambda _: [_build_session(start_time=1773666732475)],
    )
    monkeypatch.setattr("builtins.input", lambda _: "")

    result = prompt_start_time_overrides(tmp_path / "config.toml")

    captured = capsys.readouterr()

    assert result.should_run_pipeline is False
    assert result.start_time_overrides is None
    assert "[1] Song | Expert | S | finished | 1773666732475" in captured.out
    assert "Selection canceled." in captured.out


def _build_session(start_time: int) -> PlaySession:
    """Build a minimal session fixture for selection tests."""

    return PlaySession(
        start_time=start_time,
        end_time=start_time + 1000,
        start=start_time,
        menu_time=start_time + 1000,
        song_hash="abc12345deadbeef",
        song_name="Song",
        difficulty="Expert",
        rank="S",
        score=123,
        cleared="finished",
    )
