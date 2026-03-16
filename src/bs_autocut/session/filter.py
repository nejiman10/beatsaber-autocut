"""Filtering helpers for play sessions."""

from __future__ import annotations

from bs_autocut.config_loader import FilterConfig
from bs_autocut.models import PlaySession


def filter_sessions(
    sessions: list[PlaySession],
    filter_config: FilterConfig,
) -> list[PlaySession]:
    """Return sessions that match the configured filter criteria."""

    return [session for session in sessions if _matches_filters(session, filter_config)]


def _matches_filters(session: PlaySession, filter_config: FilterConfig) -> bool:
    """Return whether a session satisfies all configured filters."""

    if filter_config.include_cleared and session.cleared not in filter_config.include_cleared:
        return False
    if filter_config.exclude_cleared and session.cleared in filter_config.exclude_cleared:
        return False

    if filter_config.include_ranks and session.rank not in filter_config.include_ranks:
        return False
    if filter_config.exclude_ranks and session.rank in filter_config.exclude_ranks:
        return False

    if session.score < filter_config.min_score:
        return False

    if filter_config.include_song_names and not _matches_song_name_filter(
        session.song_name,
        filter_config.include_song_names,
    ):
        return False
    if filter_config.exclude_song_names and _matches_song_name_filter(
        session.song_name,
        filter_config.exclude_song_names,
    ):
        return False

    if (
        filter_config.include_difficulties
        and session.difficulty not in filter_config.include_difficulties
    ):
        return False
    if (
        filter_config.exclude_difficulties
        and session.difficulty in filter_config.exclude_difficulties
    ):
        return False

    if (
        filter_config.include_start_times
        and session.start_time not in filter_config.include_start_times
    ):
        return False
    if filter_config.exclude_start_times and session.start_time in filter_config.exclude_start_times:
        return False

    return True


def _matches_song_name_filter(song_name: str, filters: tuple[str, ...]) -> bool:
    """Return whether the song name matches any configured substring."""

    normalized_song_name = song_name.casefold()
    return any(filter_value.casefold() in normalized_song_name for filter_value in filters)
