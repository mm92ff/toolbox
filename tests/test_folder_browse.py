#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the folder-browsing feature."""
from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.features.entries.folder_browse import (
    _make_browse_entries,
    enter_folder_browse,
    exit_folder_browse,
)
from app import constants


@pytest.fixture()
def tmp_folder(tmp_path: Path) -> Path:
    """Create a temporary folder with some files and a subfolder."""
    (tmp_path / "alpha.txt").write_text("a")
    (tmp_path / "beta.exe").write_text("b")
    (tmp_path / "subdir").mkdir()
    (tmp_path / ".hidden").write_text("hidden")
    return tmp_path


def test_make_browse_entries_lists_non_hidden_items(tmp_folder: Path) -> None:
    entries = _make_browse_entries(tmp_folder)
    names = [e.title for e in entries]
    assert "subdir/" in names       # folder listed first with /
    assert "alpha.txt" in names
    assert "beta.exe" in names
    assert not any(".hidden" in n for n in names)  # hidden files excluded


def test_make_browse_entries_dirs_come_first(tmp_folder: Path) -> None:
    entries = _make_browse_entries(tmp_folder)
    # subdir should appear before files
    titles = [e.title for e in entries]
    assert titles.index("subdir/") < titles.index("alpha.txt")


def test_make_browse_entries_all_are_tool_kind(tmp_folder: Path) -> None:
    entries = _make_browse_entries(tmp_folder)
    assert all(e.kind == constants.ENTRY_KIND_TOOL for e in entries)


def test_make_browse_entries_unique_ids(tmp_folder: Path) -> None:
    entries = _make_browse_entries(tmp_folder)
    ids = [e.entry_id for e in entries]
    assert len(ids) == len(set(ids)), "Each entry must have a unique ID"


def test_make_browse_entries_empty_on_permission_error() -> None:
    with patch("app.features.entries.folder_browse.Path.iterdir", side_effect=PermissionError):
        entries = _make_browse_entries(Path("/fake"))
    assert entries == []


def _make_mock_ctx(tmp_path: Path) -> MagicMock:
    ctx = MagicMock()
    ctx.browse_stack = []
    ctx.selected_ids = set()
    ctx.entries = []
    ctx.breadcrumb_bar = None
    ctx._browse_display_entries = []
    return ctx


def _make_mock_owner() -> MagicMock:
    owner = MagicMock()
    owner.current_icon_size.return_value = 72
    owner.current_tile_frame_enabled.return_value = True
    owner.current_tile_frame_thickness.return_value = 1
    owner.current_tile_frame_color.return_value = "#fff"
    owner.current_tile_highlight_color.return_value = "#fff"
    owner.current_grid_spacing_x.return_value = 28
    owner.current_grid_spacing_y.return_value = 24
    owner.current_section_font_size.return_value = 15
    owner.current_section_line_thickness.return_value = 2
    owner.current_section_gap.return_value = 12
    owner.current_section_line_color.return_value = "#444"
    owner.current_section_gap_above.return_value = 12
    owner.current_section_gap_below.return_value = 12
    owner.current_image_file_preview_enabled.return_value = False
    owner.current_image_file_preview_mode.return_value = "fit"
    owner.current_video_file_preview_enabled.return_value = False
    owner.current_hover_preview_enabled.return_value = False
    owner.current_ffmpeg_manual_path.return_value = ""
    owner.current_auto_compact_left.return_value = True
    return owner


def test_enter_folder_browse_pushes_stack(tmp_folder: Path) -> None:
    ctx = _make_mock_ctx(tmp_folder)
    owner = _make_mock_owner()
    enter_folder_browse(owner, ctx, tmp_folder)
    assert ctx.browse_stack == [tmp_folder]


def test_enter_folder_browse_calls_set_entries(tmp_folder: Path) -> None:
    ctx = _make_mock_ctx(tmp_folder)
    owner = _make_mock_owner()
    enter_folder_browse(owner, ctx, tmp_folder)
    ctx.canvas.set_entries.assert_called_once()


def test_exit_folder_browse_pops_stack(tmp_folder: Path) -> None:
    ctx = _make_mock_ctx(tmp_folder)
    owner = _make_mock_owner()
    ctx.browse_stack = [tmp_folder]
    ctx._browse_display_entries = []
    exit_folder_browse(owner, ctx)
    assert ctx.browse_stack == []


def test_exit_folder_browse_calls_refresh_when_empty(tmp_folder: Path) -> None:
    ctx = _make_mock_ctx(tmp_folder)
    owner = _make_mock_owner()
    ctx.browse_stack = [tmp_folder]
    ctx._browse_display_entries = []
    exit_folder_browse(owner, ctx)
    owner.refresh_canvas.assert_called_once_with(ctx)


def test_exit_browse_nested_stays_in_browse(tmp_folder: Path) -> None:
    sub = tmp_folder / "subdir"
    ctx = _make_mock_ctx(tmp_folder)
    owner = _make_mock_owner()
    ctx.browse_stack = [tmp_folder, sub]
    ctx._browse_display_entries = []
    exit_folder_browse(owner, ctx)
    # One level popped, still in browse
    assert ctx.browse_stack == [tmp_folder]
    # Canvas was re-rendered with parent folder entries
    ctx.canvas.set_entries.assert_called_once()
