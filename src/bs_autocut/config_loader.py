"""Configuration loading and validation for Beat Saber auto clip tool."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import tomllib
from typing import Any

VALID_CUT_MODES = {"song", "play", "with_result"}
VALID_FFMPEG_MODES = {"reencode", "copy"}
DEFAULT_VIDEO_EXTENSIONS = ("mkv", "mp4")
DEFAULT_EXTRA_ARGS: tuple[str, ...] = ()


@dataclass(frozen=True)
class PathsConfig:
    """Filesystem locations used by the application."""

    db: Path
    videos: Path
    output: Path


@dataclass(frozen=True)
class CutConfig:
    """Clip timing behavior configuration."""

    mode: str = "song"
    pre_roll: float = 6.0
    post_roll: float = 4.0
    time_offset: float = 0.0


@dataclass(frozen=True)
class FilterConfig:
    """Session filtering configuration."""

    include_cleared: tuple[str, ...] = field(default_factory=tuple)
    exclude_cleared: tuple[str, ...] = field(default_factory=tuple)
    include_ranks: tuple[str, ...] = field(default_factory=tuple)
    exclude_ranks: tuple[str, ...] = field(default_factory=tuple)
    min_score: int = 0
    include_song_names: tuple[str, ...] = field(default_factory=tuple)
    exclude_song_names: tuple[str, ...] = field(default_factory=tuple)
    include_difficulties: tuple[str, ...] = field(default_factory=tuple)
    exclude_difficulties: tuple[str, ...] = field(default_factory=tuple)
    include_start_times: tuple[int, ...] = field(default_factory=tuple)
    exclude_start_times: tuple[int, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class VideoConfig:
    """Input video scanning configuration."""

    extensions: tuple[str, ...] = DEFAULT_VIDEO_EXTENSIONS


@dataclass(frozen=True)
class OutputConfig:
    """Output file naming and format configuration."""

    format: str = "mp4"
    filename_template: str = "{song} [{difficulty}] {rank} {score}"


@dataclass(frozen=True)
class OrganizeConfig:
    """Directory organization settings for generated clips."""

    enabled: bool = False
    path_template: str = "{song}/{difficulty}"


@dataclass(frozen=True)
class FFmpegConfig:
    """FFmpeg and ffprobe command configuration."""

    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"
    mode: str = "reencode"
    video_codec: str = "libx264"
    audio_codec: str = "aac"
    crf: int = 18
    preset: str = "fast"
    extra_input_args: tuple[str, ...] = field(default_factory=tuple)
    extra_output_args: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RunConfig:
    """Execution behavior flags."""

    dry_run: bool = False
    overwrite: bool = False


@dataclass(frozen=True)
class SelectConfig:
    """Interactive session selector configuration."""

    recent_limit: int = 20


@dataclass(frozen=True)
class AppConfig:
    """Application configuration loaded from a TOML file."""

    paths: PathsConfig
    cut: CutConfig = field(default_factory=CutConfig)
    filter: FilterConfig = field(default_factory=FilterConfig)
    video: VideoConfig = field(default_factory=VideoConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    organize: OrganizeConfig = field(default_factory=OrganizeConfig)
    ffmpeg: FFmpegConfig = field(default_factory=FFmpegConfig)
    run: RunConfig = field(default_factory=RunConfig)
    select: SelectConfig = field(default_factory=SelectConfig)


def load_config(config_path: Path) -> AppConfig:
    """Load and validate a configuration file."""

    config_path = config_path.expanduser()
    with config_path.open("rb") as file_obj:
        raw_config = tomllib.load(file_obj)

    base_dir = config_path.parent
    paths_data = _require_table(raw_config, "paths")
    cut_data = _optional_table(raw_config, "cut")
    filter_data = _optional_table(raw_config, "filter")
    video_data = _optional_table(raw_config, "video")
    output_data = _optional_table(raw_config, "output")
    organize_data = _optional_table(raw_config, "organize")
    ffmpeg_data = _optional_table(raw_config, "ffmpeg")
    run_data = _optional_table(raw_config, "run")
    select_data = _optional_table(raw_config, "select")

    config = AppConfig(
        paths=_load_paths_config(paths_data, base_dir),
        cut=_load_cut_config(cut_data),
        filter=_load_filter_config(filter_data),
        video=_load_video_config(video_data),
        output=_load_output_config(output_data),
        organize=_load_organize_config(organize_data),
        ffmpeg=_load_ffmpeg_config(ffmpeg_data),
        run=_load_run_config(run_data),
        select=_load_select_config(select_data),
    )
    _validate_config(config)
    return config


def _optional_table(data: dict[str, Any], key: str) -> dict[str, Any]:
    """Return a TOML table if present, otherwise an empty mapping."""

    value = data.get(key, {})
    if not isinstance(value, dict):
        raise ValueError(f"Configuration section '{key}' must be a table.")
    return value


def _require_table(data: dict[str, Any], key: str) -> dict[str, Any]:
    """Return a required TOML table."""

    if key not in data:
        raise ValueError(f"Missing required configuration section '{key}'.")
    return _optional_table(data, key)


def _read_required_path(data: dict[str, Any], key: str, base_dir: Path) -> Path:
    """Read a required path value and resolve it relative to the config file."""

    if key not in data:
        raise ValueError(f"Missing required path 'paths.{key}'.")
    value = data[key]
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Configuration value 'paths.{key}' must be a non-empty string.")
    return _resolve_path(value, base_dir)


def _resolve_path(raw_path: str, base_dir: Path) -> Path:
    """Expand user markers and resolve relative paths against the config directory."""

    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path


def _read_str(data: dict[str, Any], key: str, default: str) -> str:
    """Read a string value with a default."""

    value = data.get(key, default)
    if not isinstance(value, str):
        raise ValueError(f"Configuration value '{key}' must be a string.")
    return value


def _read_bool(data: dict[str, Any], key: str, default: bool) -> bool:
    """Read a boolean value with a default."""

    value = data.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f"Configuration value '{key}' must be a boolean.")
    return value


def _read_int(data: dict[str, Any], key: str, default: int) -> int:
    """Read an integer value with a default."""

    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"Configuration value '{key}' must be an integer.")
    return value


def _read_float(data: dict[str, Any], key: str, default: float) -> float:
    """Read a numeric value with a default."""

    value = data.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"Configuration value '{key}' must be numeric.")
    return float(value)


def _read_str_list(
    data: dict[str, Any],
    key: str,
    default: tuple[str, ...],
) -> tuple[str, ...]:
    """Read a list of strings and normalize it to a tuple."""

    value = data.get(key, default)
    if not isinstance(value, list | tuple):
        raise ValueError(f"Configuration value '{key}' must be a list of strings.")
    items = tuple(value)
    if any(not isinstance(item, str) for item in items):
        raise ValueError(f"Configuration value '{key}' must be a list of strings.")
    return items


def _read_int_list(
    data: dict[str, Any],
    key: str,
    default: tuple[int, ...],
) -> tuple[int, ...]:
    """Read a list of integers and normalize it to a tuple."""

    value = data.get(key, default)
    if not isinstance(value, list | tuple):
        raise ValueError(f"Configuration value '{key}' must be a list of integers.")
    items = tuple(value)
    if any(isinstance(item, bool) or not isinstance(item, int) for item in items):
        raise ValueError(f"Configuration value '{key}' must be a list of integers.")
    return items


def _load_filter_config(filter_data: dict[str, Any]) -> FilterConfig:
    """Load the optional filter section."""

    return FilterConfig(
        include_cleared=_read_str_list(filter_data, "include_cleared", ()),
        exclude_cleared=_read_str_list(filter_data, "exclude_cleared", ()),
        include_ranks=_read_str_list(filter_data, "include_ranks", ()),
        exclude_ranks=_read_str_list(filter_data, "exclude_ranks", ()),
        min_score=_read_int(filter_data, "min_score", 0),
        include_song_names=_read_str_list(filter_data, "include_song_names", ()),
        exclude_song_names=_read_str_list(filter_data, "exclude_song_names", ()),
        include_difficulties=_read_str_list(filter_data, "include_difficulties", ()),
        exclude_difficulties=_read_str_list(filter_data, "exclude_difficulties", ()),
        include_start_times=_read_int_list(filter_data, "include_start_times", ()),
        exclude_start_times=_read_int_list(filter_data, "exclude_start_times", ()),
    )


def _load_paths_config(paths_data: dict[str, Any], base_dir: Path) -> PathsConfig:
    """Load the required paths section."""

    return PathsConfig(
        db=_read_required_path(paths_data, "db", base_dir),
        videos=_read_required_path(paths_data, "videos", base_dir),
        output=_read_required_path(paths_data, "output", base_dir),
    )


def _load_cut_config(cut_data: dict[str, Any]) -> CutConfig:
    """Load the optional cut section."""

    return CutConfig(
        mode=_read_str(cut_data, "mode", "song"),
        pre_roll=_read_float(cut_data, "pre_roll", 6.0),
        post_roll=_read_float(cut_data, "post_roll", 4.0),
        time_offset=_read_float(cut_data, "time_offset", 0.0),
    )


def _load_video_config(video_data: dict[str, Any]) -> VideoConfig:
    """Load the optional video section."""

    return VideoConfig(
        extensions=_read_str_list(video_data, "extensions", DEFAULT_VIDEO_EXTENSIONS),
    )


def _load_output_config(output_data: dict[str, Any]) -> OutputConfig:
    """Load the optional output section."""

    return OutputConfig(
        format=_read_str(output_data, "format", "mp4"),
        filename_template=_read_str(
            output_data,
            "filename_template",
            "{song} [{difficulty}] {rank} {score}",
        ),
    )


def _load_organize_config(organize_data: dict[str, Any]) -> OrganizeConfig:
    """Load the optional organize section."""

    return OrganizeConfig(
        enabled=_read_bool(organize_data, "enabled", False),
        path_template=_read_str(organize_data, "path_template", "{song}/{difficulty}"),
    )


def _load_ffmpeg_config(ffmpeg_data: dict[str, Any]) -> FFmpegConfig:
    """Load the optional ffmpeg section."""

    return FFmpegConfig(
        ffmpeg_bin=_read_str(ffmpeg_data, "ffmpeg_bin", "ffmpeg"),
        ffprobe_bin=_read_str(ffmpeg_data, "ffprobe_bin", "ffprobe"),
        mode=_read_str(ffmpeg_data, "mode", "reencode"),
        video_codec=_read_str(ffmpeg_data, "video_codec", "libx264"),
        audio_codec=_read_str(ffmpeg_data, "audio_codec", "aac"),
        crf=_read_int(ffmpeg_data, "crf", 18),
        preset=_read_str(ffmpeg_data, "preset", "fast"),
        extra_input_args=_read_str_list(ffmpeg_data, "extra_input_args", DEFAULT_EXTRA_ARGS),
        extra_output_args=_read_str_list(ffmpeg_data, "extra_output_args", DEFAULT_EXTRA_ARGS),
    )


def _load_run_config(run_data: dict[str, Any]) -> RunConfig:
    """Load the optional run section."""

    return RunConfig(
        dry_run=_read_bool(run_data, "dry_run", False),
        overwrite=_read_bool(run_data, "overwrite", False),
    )


def _load_select_config(select_data: dict[str, Any]) -> SelectConfig:
    """Load the optional select section."""

    return SelectConfig(
        recent_limit=_read_int(select_data, "recent_limit", 20),
    )


def _validate_config(config: AppConfig) -> None:
    """Validate cross-field constraints for the loaded configuration."""

    if config.cut.mode not in VALID_CUT_MODES:
        valid_modes = ", ".join(sorted(VALID_CUT_MODES))
        raise ValueError(f"Invalid cut mode '{config.cut.mode}'. Expected one of: {valid_modes}.")

    if config.ffmpeg.mode not in VALID_FFMPEG_MODES:
        valid_modes = ", ".join(sorted(VALID_FFMPEG_MODES))
        raise ValueError(
            f"Invalid ffmpeg mode '{config.ffmpeg.mode}'. Expected one of: {valid_modes}."
        )

    for name, path in (
        ("paths.db", config.paths.db),
        ("paths.videos", config.paths.videos),
        ("paths.output", config.paths.output),
    ):
        if not str(path):
            raise ValueError(f"Configuration value '{name}' must not be empty.")

    if config.select.recent_limit < 1:
        raise ValueError("Configuration value 'select.recent_limit' must be at least 1.")
