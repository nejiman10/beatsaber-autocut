"""Helpers for building sanitized clip output filenames."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from bs_autocut.models import PlaySession

INVALID_FILENAME_CHARACTERS = str.maketrans({char: "_" for char in '/\\:*?"<>|'})
MAX_FILENAME_LENGTH = 200
TIMESTAMP_MS_THRESHOLD = 1e12


def build_unique_id(session: PlaySession) -> str:
    """Build the stable unique identifier for a clip."""

    return f"{session.start_time}_{session.song_hash[:8]}"


def sanitize_filename(value: str) -> str:
    """Replace invalid filename characters and trim surrounding whitespace."""

    return value.translate(INVALID_FILENAME_CHARACTERS).strip()


def build_filename(session: PlaySession, template: str, ext: str) -> str:
    """Build a sanitized clip filename from a template and file extension."""

    template_values = _build_template_values(session)
    rendered_template = template.format(**template_values)
    sanitized_template = sanitize_filename(rendered_template)
    unique_id = sanitize_filename(build_unique_id(session))
    normalized_ext = _normalize_extension(ext)

    filename = f"{sanitized_template}__{unique_id}.{normalized_ext}"
    if len(filename) <= MAX_FILENAME_LENGTH:
        return filename

    suffix = f"__{unique_id}.{normalized_ext}"
    max_template_length = MAX_FILENAME_LENGTH - len(suffix)
    trimmed_template = sanitized_template[: max(0, max_template_length)].rstrip(" .")

    if trimmed_template:
        return f"{trimmed_template}{suffix}"
    return f"{unique_id}.{normalized_ext}"


def _build_template_values(session: PlaySession) -> dict[str, str]:
    """Build the supported template variables for a session."""

    start_datetime = _datetime_from_timestamp(session.start_time)
    return {
        "song": session.song_name,
        "difficulty": session.difficulty,
        "rank": session.rank,
        "score": str(session.score),
        "hash": session.song_hash,
        "start_time": str(session.start_time),
        "date": start_datetime.strftime("%Y-%m-%d"),
        "time": start_datetime.strftime("%H-%M-%S"),
    }


def _datetime_from_timestamp(timestamp: int) -> datetime:
    """Convert a session timestamp to a local datetime, handling milliseconds."""

    normalized_timestamp = float(timestamp)
    if normalized_timestamp > TIMESTAMP_MS_THRESHOLD:
        normalized_timestamp /= 1000.0
    return datetime.fromtimestamp(normalized_timestamp)


def _normalize_extension(ext: str) -> str:
    """Normalize an output extension to a bare suffix without a leading dot."""

    normalized = ext.strip()
    if not normalized:
        raise ValueError("File extension must not be empty.")
    suffix = Path(f"file.{normalized.lstrip('.')}").suffix.lstrip(".")
    if not suffix:
        raise ValueError("File extension must not be empty.")
    return suffix
