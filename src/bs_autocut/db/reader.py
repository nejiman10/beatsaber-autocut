"""SQLite reader for Beat Saber play session records."""

from __future__ import annotations

from pathlib import Path
import sqlite3

from bs_autocut.models import PlaySession

MOVIE_CUT_RECORD_QUERY = """
SELECT
    startTime,
    endTime,
    start,
    menuTime,
    songHash,
    songName,
    difficulty,
    rank,
    score,
    cleared
FROM MovieCutRecord
ORDER BY startTime;
"""


def read_sessions_from_db(database_path: Path) -> list[PlaySession]:
    """Read play sessions from the MovieCutRecord table in the SQLite database."""

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row

    try:
        cursor = connection.execute(MOVIE_CUT_RECORD_QUERY)
        rows = cursor.fetchall()
    finally:
        connection.close()

    return [_row_to_play_session(row) for row in rows]


def _row_to_play_session(row: sqlite3.Row) -> PlaySession:
    """Convert a database row into a PlaySession instance."""

    return PlaySession(
        start_time=_read_int(row, "startTime", default=0),
        end_time=_read_int(row, "endTime", default=0),
        start=_read_optional_int(row, "start"),
        menu_time=_read_optional_int(row, "menuTime"),
        song_hash=_read_str(row, "songHash", default=""),
        song_name=_read_str(row, "songName", default=""),
        difficulty=_read_str(row, "difficulty", default=""),
        rank=_read_str(row, "rank", default=""),
        score=_read_int(row, "score", default=0),
        cleared=_read_str(row, "cleared", default=""),
    )


def _read_int(row: sqlite3.Row, key: str, default: int) -> int:
    """Read an integer column value, returning a default when absent or null."""

    value = _read_value(row, key, default)
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    return int(value)


def _read_optional_int(row: sqlite3.Row, key: str) -> int | None:
    """Read an optional integer column value, returning None when absent or null."""

    value = _read_value(row, key, None)
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    return int(value)


def _read_str(row: sqlite3.Row, key: str, default: str) -> str:
    """Read a string column value, returning a default when absent or null."""

    value = _read_value(row, key, default)
    if value is None:
        return default
    if isinstance(value, str):
        return value
    return str(value)


def _read_value(row: sqlite3.Row, key: str, default: object) -> object:
    """Safely read a column value from a sqlite3.Row."""

    try:
        return row[key]
    except (IndexError, KeyError):
        return default
