#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the folder-browsing feature."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.features.entries.folder_browse import (
    _apply_browse_layout,
    _make_browse_entries,
    _refresh_browse_view,
    effective_folder_icon_size,
    enter_folder_browse,
    exit_folder_browse,
)
from app import constants
from app.features.entries.controller_context_menu import show_canvas_context_menu
from app.features.entries.controller_selection import entries_for_current_view
from app.state.folder_browse_appearance import FolderBrowseAppearanceStore
from app.ui.tabs.toolbox_tab import create_toolbox_tab


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
        with pytest.raises(OSError, match="Keine Leseberechtigung"):
            _make_browse_entries(Path("/fake"))


def test_broken_symlink_does_not_break_or_pollute_view(tmp_path: Path) -> None:
    (tmp_path / "broken").symlink_to(tmp_path / "missing")
    (tmp_path / "valid.txt").write_text("ok", encoding="utf-8")

    entries = _make_browse_entries(tmp_path)

    assert [entry.title for entry in entries] == ["valid.txt"]


def _make_mock_ctx(tmp_path: Path) -> MagicMock:
    ctx = MagicMock()
    ctx.browse_stack = []
    ctx.selected_ids = set()
    ctx.entries = []
    ctx.search_input.text.return_value = ""
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
    owner.current_preview_overlay_enabled.return_value = False
    owner.current_hover_preview_enabled.return_value = False
    owner.current_ffmpeg_manual_path.return_value = ""
    owner.current_auto_compact_left.return_value = True
    owner.current_folder_show_file_count.return_value = True
    owner.current_show_tooltips.return_value = False
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


def test_browse_refresh_uses_folder_override(tmp_folder: Path) -> None:
    ctx = _make_mock_ctx(tmp_folder)
    owner = _make_mock_owner()
    owner._folder_browse_appearance_store = FolderBrowseAppearanceStore()
    owner._folder_browse_appearance_store.set_icon_size(tmp_folder, 124)
    ctx.browse_stack = [tmp_folder]

    assert _refresh_browse_view(owner, ctx) is True

    assert ctx.canvas.set_entries.call_args.args[2] == 124


def test_effective_browse_size_follows_global_value_without_override(
    tmp_folder: Path,
) -> None:
    owner = _make_mock_owner()
    owner.current_icon_size.return_value = 88
    owner._folder_browse_appearance_store = FolderBrowseAppearanceStore()

    assert effective_folder_icon_size(owner, tmp_folder) == 88

    owner.current_icon_size.return_value = 104
    assert effective_folder_icon_size(owner, tmp_folder) == 104


def test_toolbox_tab_contains_hidden_folder_size_controls() -> None:
    _page, widgets = create_toolbox_tab()
    breadcrumb = widgets[constants.WIDGET_BROWSE_BREADCRUMB_BAR]
    slider = widgets[constants.WIDGET_BROWSE_ICON_SIZE_SLIDER]
    reset = widgets[constants.BUTTON_BROWSE_ICON_SIZE_RESET]

    assert breadcrumb.isHidden()
    assert slider.minimum() == constants.MIN_ICON_SIZE
    assert slider.maximum() == constants.MAX_ICON_SIZE
    assert slider.accessibleName()
    assert reset.isEnabled() is False


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


def test_browse_refresh_preserves_stable_selection_and_passes_display_settings(
    tmp_folder: Path,
) -> None:
    ctx = _make_mock_ctx(tmp_folder)
    owner = _make_mock_owner()
    ctx.browse_stack = [tmp_folder]
    assert _refresh_browse_view(owner, ctx) is True
    selected_id = ctx._browse_display_entries[0].entry_id
    ctx.selected_ids = {selected_id}

    assert _refresh_browse_view(owner, ctx) is True

    assert ctx.selected_ids == {selected_id}
    kwargs = ctx.canvas.set_entries.call_args.kwargs
    assert kwargs["folder_show_file_count"] is True
    assert kwargs["show_tooltips"] is False


@pytest.mark.parametrize(
    ("automatic_font", "expected_font_size"),
    ((True, None), (False, 19)),
)
def test_browse_layout_preserves_automatic_or_fixed_font_mode(
    tmp_folder: Path,
    automatic_font: bool,
    expected_font_size: int | None,
) -> None:
    ctx = _make_mock_ctx(tmp_folder)
    owner = _make_mock_owner()
    ctx.browse_stack = [tmp_folder]
    owner.current_tile_font_auto.return_value = automatic_font
    owner.current_tile_font_size.return_value = 19

    _apply_browse_layout(owner, ctx, icon_size=108)

    assert ctx.canvas.apply_layout_settings.call_args.args[1] == 108
    assert (
        ctx.canvas.apply_layout_settings.call_args.kwargs["tile_font_size"]
        == expected_font_size
    )


def test_entries_for_current_view_returns_browse_entries(tmp_folder: Path) -> None:
    ctx = _make_mock_ctx(tmp_folder)
    ctx.entries = [MagicMock(entry_id="stored")]
    ctx.browse_stack = [tmp_folder]
    ctx._browse_display_entries = [MagicMock(entry_id="visible")]

    assert [entry.entry_id for entry in entries_for_current_view(ctx)] == ["visible"]


def test_browse_context_menu_contains_only_read_only_actions(tmp_folder: Path) -> None:
    ctx = _make_mock_ctx(tmp_folder)
    entry = _make_browse_entries(tmp_folder)[0]
    ctx.browse_stack = [tmp_folder]
    ctx._browse_display_entries = [entry]
    owner = _make_mock_owner()
    menu = MagicMock()
    menu.exec.return_value = None

    with patch(
        "app.features.entries.controller_context_menu.QtWidgets.QMenu",
        return_value=menu,
    ):
        show_canvas_context_menu(owner, ctx, entry.entry_id, MagicMock())

    labels = [call.args[0] for call in menu.addAction.call_args_list]
    assert labels == ["Ordner öffnen", "Im Dateimanager anzeigen"]
    assert not any(label in labels for label in ("Remove", "Rename", "Eigenschaften bearbeiten"))
