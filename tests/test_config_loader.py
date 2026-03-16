"""Tests for configuration loading."""

from __future__ import annotations

from pathlib import Path

from bs_autocut.config_loader import load_config


def test_load_config_defaults_cut_time_offset_to_zero(tmp_path: Path) -> None:
    """Missing cut.time_offset should default to 0.0."""

    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "\n".join(
            [
                "[paths]",
                'db = "./beatsaber.db"',
                'videos = "./videos"',
                'output = "./clips"',
                "",
                "[cut]",
                'mode = "song"',
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.cut.time_offset == 0.0


def test_load_config_reads_cut_time_offset_as_float(tmp_path: Path) -> None:
    """Configured cut.time_offset should be read as a float."""

    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "\n".join(
            [
                "[paths]",
                'db = "./beatsaber.db"',
                'videos = "./videos"',
                'output = "./clips"',
                "",
                "[cut]",
                'time_offset = -1.25',
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.cut.time_offset == -1.25


def test_load_config_defaults_filter_values(tmp_path: Path) -> None:
    """Missing filter section should use the default filter values."""

    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "\n".join(
            [
                "[paths]",
                'db = "./beatsaber.db"',
                'videos = "./videos"',
                'output = "./clips"',
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.filter.include_cleared == ()
    assert config.filter.exclude_cleared == ()
    assert config.filter.include_ranks == ()
    assert config.filter.exclude_ranks == ()
    assert config.filter.min_score == 0
    assert config.filter.include_song_names == ()
    assert config.filter.exclude_song_names == ()
    assert config.filter.include_difficulties == ()
    assert config.filter.exclude_difficulties == ()
    assert config.filter.include_start_times == ()
    assert config.filter.exclude_start_times == ()
    assert config.select.recent_limit == 20


def test_load_config_reads_filter_values(tmp_path: Path) -> None:
    """Configured filter values should be loaded with the expected types."""

    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "\n".join(
            [
                "[paths]",
                'db = "./beatsaber.db"',
                'videos = "./videos"',
                'output = "./clips"',
                "",
                "[filter]",
                'include_cleared = ["true", "false"]',
                'exclude_cleared = ["maybe"]',
                'include_ranks = ["S", "SS"]',
                'exclude_ranks = ["D"]',
                "min_score = 12345",
                'include_song_names = ["Idol", "HIBANA"]',
                'exclude_song_names = ["Tutorial"]',
                'include_difficulties = ["Expert", "ExpertPlus"]',
                'exclude_difficulties = ["Easy"]',
                "include_start_times = [1710000123, 1710000456]",
                "exclude_start_times = [1710000789]",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.filter.include_cleared == ("true", "false")
    assert config.filter.exclude_cleared == ("maybe",)
    assert config.filter.include_ranks == ("S", "SS")
    assert config.filter.exclude_ranks == ("D",)
    assert config.filter.min_score == 12345
    assert config.filter.include_song_names == ("Idol", "HIBANA")
    assert config.filter.exclude_song_names == ("Tutorial",)
    assert config.filter.include_difficulties == ("Expert", "ExpertPlus")
    assert config.filter.exclude_difficulties == ("Easy",)
    assert config.filter.include_start_times == (1710000123, 1710000456)
    assert config.filter.exclude_start_times == (1710000789,)


def test_load_config_reads_select_recent_limit(tmp_path: Path) -> None:
    """Configured select.recent_limit should be loaded as an integer."""

    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "\n".join(
            [
                "[paths]",
                'db = "./beatsaber.db"',
                'videos = "./videos"',
                'output = "./clips"',
                "",
                "[select]",
                "recent_limit = 7",
            ]
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.select.recent_limit == 7
