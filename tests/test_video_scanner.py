"""Tests for video file scanning helpers."""

from __future__ import annotations

from pathlib import Path

from bs_autocut.video.scanner import scan_video_files


def test_scan_video_files_filters_extensions_case_insensitively(tmp_path: Path) -> None:
    """Scanner should only keep matching file extensions regardless of case."""

    (tmp_path / "a.MKV").write_text("")
    (tmp_path / "b.mp4").write_text("")
    (tmp_path / "c.txt").write_text("")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "d.mkv").write_text("")

    paths = scan_video_files(tmp_path, ["mkv", ".MP4"])

    assert paths == [tmp_path / "a.MKV", tmp_path / "b.mp4"]


def test_scan_video_files_sorts_by_name(tmp_path: Path) -> None:
    """Scanner should return matching files sorted by path name."""

    (tmp_path / "zeta.mp4").write_text("")
    (tmp_path / "Alpha.mp4").write_text("")

    paths = scan_video_files(tmp_path, ["mp4"])

    assert paths == [tmp_path / "Alpha.mp4", tmp_path / "zeta.mp4"]
