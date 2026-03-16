"""Filesystem scanning helpers for locating source video files."""

from __future__ import annotations

from pathlib import Path


def scan_video_files(directory: Path, extensions: list[str]) -> list[Path]:
    """Return sorted video file paths from a directory for the allowed extensions."""

    normalized_extensions = _normalize_extensions(extensions)
    if not normalized_extensions:
        return []

    video_paths = [
        path
        for path in directory.iterdir()
        if path.is_file() and _has_allowed_extension(path, normalized_extensions)
    ]
    return sorted(video_paths, key=_sort_key)


def _normalize_extensions(extensions: list[str]) -> set[str]:
    """Normalize configured extensions for case-insensitive comparisons."""

    return {
        extension.casefold().lstrip(".")
        for extension in extensions
        if extension.strip()
    }


def _has_allowed_extension(path: Path, normalized_extensions: set[str]) -> bool:
    """Return True when a path suffix is in the allowed extension set."""

    suffix = path.suffix.casefold().lstrip(".")
    return bool(suffix) and suffix in normalized_extensions


def _sort_key(path: Path) -> tuple[str, str]:
    """Sort by file name first and full path second for deterministic output."""

    return path.name.casefold(), str(path)
