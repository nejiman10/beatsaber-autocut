"""Command-line entrypoint for the Beat Saber auto clip tool."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import logging
from pathlib import Path
import sys

from bs_autocut.cli_select import prompt_start_time_overrides
from bs_autocut.orchestrator import run_pipeline

USAGE = "Usage: bs-autocut config.toml [--start-time <integer> ...]\n       bs-autocut config.toml select"


@dataclass(frozen=True)
class ParsedArgs:
    """Parsed command-line arguments."""

    config_path: Path
    include_start_times_override: list[int] | None
    select_mode: bool = False


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI entrypoint."""

    args = list(sys.argv[1:] if argv is None else argv)
    parsed_args = _parse_args(args)
    if parsed_args is None:
        print(USAGE, file=sys.stderr)
        return 1

    config_path = parsed_args.config_path
    if not config_path.exists():
        print(f"Error: config file not found: {config_path}", file=sys.stderr)
        return 1

    _configure_logging()
    include_start_times_override = parsed_args.include_start_times_override
    if parsed_args.select_mode:
        select_result = prompt_start_time_overrides(config_path)
        if not select_result.should_run_pipeline:
            return 0
        include_start_times_override = select_result.start_time_overrides

    run_pipeline(
        config_path,
        include_start_times_override=include_start_times_override,
    )
    return 0


def _parse_args(args: list[str]) -> ParsedArgs | None:
    """Parse supported CLI arguments."""

    config_path: Path | None = None
    include_start_times_override: list[int] = []
    select_mode = False
    index = 0
    while index < len(args):
        arg = args[index]
        if arg == "--start-time":
            if select_mode:
                return None
            index += 1
            if index >= len(args):
                return None
            start_time = _parse_start_time_arg(args[index])
            if start_time is None:
                return None
            include_start_times_override.append(start_time)
        elif arg == "select":
            if config_path is None or include_start_times_override or select_mode:
                return None
            select_mode = True
        elif config_path is None:
            config_path = Path(arg)
        else:
            return None
        index += 1

    if config_path is None:
        return None

    return ParsedArgs(
        config_path=config_path,
        include_start_times_override=include_start_times_override or None,
        select_mode=select_mode,
    )


def _parse_start_time_arg(value: str) -> int | None:
    """Parse one ``--start-time`` value."""

    try:
        return int(value)
    except ValueError:
        return None


def _configure_logging() -> None:
    """Configure root logging if needed."""

    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    logging.basicConfig(level=logging.INFO, format="%(message)s")


if __name__ == "__main__":
    raise SystemExit(main())
