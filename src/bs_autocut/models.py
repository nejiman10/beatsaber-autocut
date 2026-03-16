"""Core domain models for Beat Saber auto clip generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PlaySession:
    """Represents one song play recorded in the DataRecorder database."""

    start_time: int
    end_time: int
    start: int | None
    menu_time: int | None
    song_hash: str
    song_name: str
    difficulty: str
    rank: str
    score: int
    cleared: str


@dataclass(frozen=True)
class VideoFile:
    """Represents one OBS recording file and its timing metadata."""

    path: Path
    start_time: float
    duration: float


@dataclass(frozen=True)
class ClipPlan:
    """Represents a planned clip extracted from a source recording."""

    video_path: Path
    start_sec: float
    end_sec: float
    output_path: Path
    session: PlaySession
