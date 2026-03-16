"""Interactive session selection helpers for the CLI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bs_autocut.config_loader import load_config
from bs_autocut.db.reader import read_sessions_from_db
from bs_autocut.models import PlaySession
from bs_autocut.session.filter import filter_sessions


@dataclass(frozen=True)
class SelectResult:
    """Interactive selector result."""

    start_time_overrides: list[int] | None
    should_run_pipeline: bool


def prompt_start_time_overrides(config_path: Path) -> SelectResult:
    """Prompt for session selection and return start-time overrides."""

    config = load_config(config_path)
    sessions = read_sessions_from_db(config.paths.db)
    filtered_sessions = filter_sessions(sessions, config.filter)
    selectable_sessions = recent_sessions(filtered_sessions, config.select.recent_limit)

    if not selectable_sessions:
        print("No sessions matched the configured filters.")
        return _cancel_selection()

    for index, session in enumerate(selectable_sessions, start=1):
        print(format_session_row(index, session))

    while True:
        selection_text = input("Select session numbers (empty to cancel): ")
        if not selection_text.strip():
            print("Selection canceled.")
            return _cancel_selection()
        try:
            return SelectResult(
                start_time_overrides=selected_start_times_from_input(
                    selection_text,
                    selectable_sessions,
                ),
                should_run_pipeline=True,
            )
        except ValueError as error:
            print(f"Error: {error}")


def recent_sessions(sessions: list[PlaySession], recent_limit: int) -> list[PlaySession]:
    """Return the most recent sessions by start_time."""

    return sorted(sessions, key=lambda session: session.start_time, reverse=True)[:recent_limit]


def format_session_row(index: int, session: PlaySession) -> str:
    """Format one selectable session row for terminal output."""

    return (
        f"[{index}] {session.song_name} | {session.difficulty} | {session.rank} | "
        f"{session.cleared} | {session.start_time}"
    )


def parse_selection(selection_text: str, max_index: int) -> list[int]:
    """Parse a comma-separated list of 1-based indices."""

    if max_index < 1:
        raise ValueError("no sessions are available")

    selected_indices: list[int] = []
    for raw_part in selection_text.split(","):
        part = raw_part.strip()
        if not part:
            raise ValueError("selection must contain only session numbers")
        try:
            selected_index = int(part)
        except ValueError as exc:
            raise ValueError("selection must contain only session numbers") from exc
        if selected_index < 1 or selected_index > max_index:
            raise ValueError(f"selection {selected_index} is out of range")
        selected_indices.append(selected_index)

    if not selected_indices:
        raise ValueError("at least one session number is required")

    return selected_indices


def selected_start_times_from_input(
    selection_text: str,
    sessions: list[PlaySession],
) -> list[int]:
    """Convert selected row numbers to session start times."""

    selected_indices = parse_selection(selection_text, len(sessions))
    return [sessions[selected_index - 1].start_time for selected_index in selected_indices]


def _cancel_selection() -> SelectResult:
    """Return the standard canceled-selection result."""

    return SelectResult(start_time_overrides=None, should_run_pipeline=False)
