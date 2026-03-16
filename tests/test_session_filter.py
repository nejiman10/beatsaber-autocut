"""Tests for session filtering."""

from __future__ import annotations

from bs_autocut.config_loader import FilterConfig
from bs_autocut.models import PlaySession
from bs_autocut.session.filter import filter_sessions


def test_filter_sessions_include_cleared() -> None:
    """Include-cleared filters should keep exact cleared matches."""

    sessions = [
        _build_session(start_time=100, cleared="true"),
        _build_session(start_time=200, cleared="false"),
    ]

    filtered = filter_sessions(sessions, FilterConfig(include_cleared=("true",)))

    assert filtered == [sessions[0]]


def test_filter_sessions_exclude_cleared() -> None:
    """Exclude-cleared filters should remove exact cleared matches."""

    sessions = [
        _build_session(start_time=100, cleared="true"),
        _build_session(start_time=200, cleared="false"),
    ]

    filtered = filter_sessions(sessions, FilterConfig(exclude_cleared=("false",)))

    assert filtered == [sessions[0]]


def test_filter_sessions_include_ranks() -> None:
    """Include-rank filters should keep exact rank matches."""

    sessions = [
        _build_session(start_time=100, rank="SS"),
        _build_session(start_time=200, rank="A"),
    ]

    filtered = filter_sessions(sessions, FilterConfig(include_ranks=("SS",)))

    assert filtered == [sessions[0]]


def test_filter_sessions_min_score() -> None:
    """Minimum score should keep sessions at or above the threshold."""

    sessions = [
        _build_session(start_time=100, score=999_999),
        _build_session(start_time=200, score=1_000_000),
    ]

    filtered = filter_sessions(sessions, FilterConfig(min_score=1_000_000))

    assert filtered == [sessions[1]]


def test_filter_sessions_include_song_names_case_insensitive() -> None:
    """Song-name filters should match case-insensitive substrings."""

    sessions = [
        _build_session(start_time=100, song_name="Blue Zenith"),
        _build_session(start_time=200, song_name="Red Shift"),
    ]

    filtered = filter_sessions(sessions, FilterConfig(include_song_names=("zen",)))

    assert filtered == [sessions[0]]


def test_filter_sessions_include_start_times() -> None:
    """Start-time filters should keep exact integer matches."""

    sessions = [
        _build_session(start_time=100),
        _build_session(start_time=200),
    ]

    filtered = filter_sessions(sessions, FilterConfig(include_start_times=(200,)))

    assert filtered == [sessions[1]]


def test_filter_sessions_combined_filters() -> None:
    """Sessions should satisfy every configured filter to be retained."""

    sessions = [
        _build_session(
            start_time=100,
            cleared="true",
            rank="SS",
            score=1_200_000,
            song_name="Blue Zenith",
            difficulty="Expert+",
        ),
        _build_session(
            start_time=200,
            cleared="true",
            rank="A",
            score=1_300_000,
            song_name="Blue Zenith",
            difficulty="Expert+",
        ),
        _build_session(
            start_time=300,
            cleared="true",
            rank="SS",
            score=1_300_000,
            song_name="Red Shift",
            difficulty="Expert+",
        ),
        _build_session(
            start_time=400,
            cleared="true",
            rank="SS",
            score=1_300_000,
            song_name="Blue Zenith",
            difficulty="Hard",
        ),
        _build_session(
            start_time=500,
            cleared="true",
            rank="SS",
            score=1_300_000,
            song_name="Blue Zenith",
            difficulty="Expert+",
        ),
    ]

    filter_config = FilterConfig(
        include_cleared=("true",),
        include_ranks=("SS",),
        min_score=1_250_000,
        include_song_names=("blue",),
        include_difficulties=("Expert+",),
        include_start_times=(100, 400, 500),
        exclude_start_times=(100,),
    )

    filtered = filter_sessions(sessions, filter_config)

    assert filtered == [sessions[4]]


def _build_session(
    *,
    start_time: int,
    end_time: int = 999,
    start: int | None = 111,
    menu_time: int | None = 222,
    song_hash: str = "abcdef0123456789",
    song_name: str = "Song",
    difficulty: str = "Expert",
    rank: str = "S",
    score: int = 123_456,
    cleared: str = "true",
) -> PlaySession:
    """Build a play session for tests."""

    return PlaySession(
        start_time=start_time,
        end_time=end_time,
        start=start,
        menu_time=menu_time,
        song_hash=song_hash,
        song_name=song_name,
        difficulty=difficulty,
        rank=rank,
        score=score,
        cleared=cleared,
    )
