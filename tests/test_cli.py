"""Tests for the command-line entrypoint."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from bs_autocut.cli import main
from bs_autocut.cli_select import SelectResult


def test_main_prints_usage_when_argument_is_missing(capsys: pytest.CaptureFixture[str]) -> None:
    """CLI should reject missing arguments with a usage message."""

    exit_code = main([])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert (
        captured.err
        == "Usage: bs-autocut config.toml [--start-time <integer> ...]\n"
        "       bs-autocut config.toml select\n"
    )


def test_main_prints_error_when_config_does_not_exist(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI should reject a missing configuration file."""

    exit_code = main([str(tmp_path / "missing.toml")])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert "Error: config file not found:" in captured.err


def test_main_runs_pipeline_with_config_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI should pass the provided config path into the orchestrator."""

    config_path = tmp_path / "config.toml"
    config_path.write_text("", encoding="utf-8")
    called_with: list[tuple[Path, list[int] | None]] = []

    monkeypatch.setattr(
        "bs_autocut.cli.run_pipeline",
        lambda path, include_start_times_override=None: called_with.append(
            (path, include_start_times_override)
        ),
    )

    exit_code = main([str(config_path)])

    assert exit_code == 0
    assert called_with == [(config_path, None)]


def test_main_runs_pipeline_with_single_start_time_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI should forward a single start-time override to the orchestrator."""

    config_path = tmp_path / "config.toml"
    config_path.write_text("", encoding="utf-8")
    called_with: list[tuple[Path, list[int] | None]] = []

    monkeypatch.setattr(
        "bs_autocut.cli.run_pipeline",
        lambda path, include_start_times_override=None: called_with.append(
            (path, include_start_times_override)
        ),
    )

    exit_code = main([str(config_path), "--start-time", "1773667651978"])

    assert exit_code == 0
    assert called_with == [(config_path, [1773667651978])]


def test_main_runs_pipeline_with_multiple_start_time_overrides(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI should collect repeated start-time overrides in order."""

    config_path = tmp_path / "config.toml"
    config_path.write_text("", encoding="utf-8")
    called_with: list[tuple[Path, list[int] | None]] = []

    monkeypatch.setattr(
        "bs_autocut.cli.run_pipeline",
        lambda path, include_start_times_override=None: called_with.append(
            (path, include_start_times_override)
        ),
    )

    exit_code = main(
        [
            str(config_path),
            "--start-time",
            "1773667651978",
            "--start-time",
            "1773666727739",
        ]
    )

    assert exit_code == 0
    assert called_with == [(config_path, [1773667651978, 1773666727739])]


def test_main_runs_selector_then_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Select mode should resolve start-time overrides before running the pipeline."""

    config_path = tmp_path / "config.toml"
    config_path.write_text("", encoding="utf-8")
    called_with: list[tuple[Path, list[int] | None]] = []

    monkeypatch.setattr(
        "bs_autocut.cli.prompt_start_time_overrides",
        lambda path: (
            SelectResult(
                start_time_overrides=[1773667651978, 1773666727739],
                should_run_pipeline=True,
            )
            if path == config_path
            else SelectResult(start_time_overrides=None, should_run_pipeline=False)
        ),
    )
    monkeypatch.setattr(
        "bs_autocut.cli.run_pipeline",
        lambda path, include_start_times_override=None: called_with.append(
            (path, include_start_times_override)
        ),
    )

    exit_code = main([str(config_path), "select"])

    assert exit_code == 0
    assert called_with == [(config_path, [1773667651978, 1773666727739])]


def test_main_does_not_run_pipeline_when_selector_cancels(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Select mode should exit successfully without running the pipeline on cancel."""

    config_path = tmp_path / "config.toml"
    config_path.write_text("", encoding="utf-8")
    called_with: list[tuple[Path, list[int] | None]] = []

    monkeypatch.setattr(
        "bs_autocut.cli.prompt_start_time_overrides",
        lambda _: SelectResult(start_time_overrides=None, should_run_pipeline=False),
    )
    monkeypatch.setattr(
        "bs_autocut.cli.run_pipeline",
        lambda path, include_start_times_override=None: called_with.append(
            (path, include_start_times_override)
        ),
    )

    exit_code = main([str(config_path), "select"])

    assert exit_code == 0
    assert called_with == []


def test_main_configures_logging_when_no_handlers_exist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI should initialize logging so orchestrator info logs are visible."""

    config_path = tmp_path / "config.toml"
    config_path.write_text("", encoding="utf-8")

    root_logger = logging.getLogger()
    original_handlers = list(root_logger.handlers)
    original_level = root_logger.level

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    monkeypatch.setattr(
        "bs_autocut.cli.run_pipeline",
        lambda _, include_start_times_override=None: None,
    )

    try:
        exit_code = main([str(config_path)])
        assert exit_code == 0
        assert root_logger.handlers
        assert root_logger.level == logging.INFO
    finally:
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
            handler.close()
        for handler in original_handlers:
            root_logger.addHandler(handler)
        root_logger.setLevel(original_level)
