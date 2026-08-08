#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Folder-browsing logic for the toolbox canvas."""

from __future__ import annotations

import uuid
from pathlib import Path

from app import constants
from app.domain.models import ToolboxEntry
from app.domain.tab_context import ToolboxTabContext


def _make_browse_entries(folder: Path) -> list[ToolboxEntry]:
    """Build a list of ToolboxEntry for the contents of *folder*."""
    entries: list[ToolboxEntry] = []
    try:
        raw_items = list(folder.iterdir())
    except PermissionError as exc:
        raise OSError(f"Keine Leseberechtigung für Ordner: {folder}") from exc
    except OSError as exc:
        raise OSError(f"Ordner kann nicht gelesen werden: {folder}: {exc}") from exc

    sortable_items: list[tuple[bool, str, Path]] = []
    for item in raw_items:
        if item.name.startswith("."):
            continue
        try:
            if item.is_symlink() and not item.exists():
                continue
            is_directory = item.is_dir()
        except OSError:
            continue
        sortable_items.append((is_directory, item.name.lower(), item))
    sortable_items.sort(key=lambda value: (not value[0], value[1]))

    x = constants.CANVAS_PADDING
    y = constants.CANVAS_PADDING
    for is_directory, _sort_name, item in sortable_items:
        normalized_path = str(item.expanduser().resolve(strict=False))
        entries.append(
            ToolboxEntry(
                title=item.name + ("/" if is_directory else ""),
                kind=constants.ENTRY_KIND_TOOL,
                path=normalized_path,
                x=x,
                y=y,
                entry_id=uuid.uuid5(uuid.NAMESPACE_URL, normalized_path).hex,
            )
        )
        x += 1  # auto-compact will position them properly
    return entries


def enter_folder_browse(owner: object, ctx: ToolboxTabContext, folder: Path) -> None:
    """Push *folder* onto the browse stack and refresh the canvas with its contents."""
    ctx.browse_stack.append(folder)
    if not _refresh_browse_view(owner, ctx):
        ctx.browse_stack.pop()


def exit_folder_browse(owner: object, ctx: ToolboxTabContext) -> None:
    """Pop one level from the browse stack; restore normal view if stack is empty."""
    if ctx.browse_stack:
        ctx.browse_stack.pop()
    if ctx.browse_stack:
        if not _refresh_browse_view(owner, ctx):
            ctx.browse_stack.clear()
            ctx._browse_display_entries = []
            _update_breadcrumb(ctx, visible=False)
            owner.refresh_canvas(ctx)
    else:
        # Back to normal
        ctx._browse_display_entries = []
        _update_breadcrumb(ctx, visible=False)
        owner.refresh_canvas(ctx)


def _refresh_browse_view(owner: object, ctx: ToolboxTabContext) -> bool:
    """Re-render the canvas with the top-of-stack folder contents."""
    folder = ctx.browse_stack[-1]
    try:
        browse_entries = _make_browse_entries(folder)
    except OSError as exc:
        owner.status.showMessage(str(exc), 5000)
        return False
    previous_selection = set(ctx.selected_ids)
    ctx._browse_display_entries = browse_entries
    _update_breadcrumb(ctx, visible=True, path=folder)

    from app.features.entries.controller_selection import hidden_entry_ids_for_context
    visible_ids = {entry.entry_id for entry in browse_entries}
    ctx.selected_ids = previous_selection & visible_ids
    ctx.canvas.set_entries(
        browse_entries,
        owner.icon_provider,
        owner.current_icon_size(),
        owner.current_tile_frame_enabled(),
        owner.current_tile_frame_thickness(),
        owner.current_tile_frame_color(),
        owner.current_tile_highlight_color(),
        owner.current_grid_spacing_x(),
        owner.current_grid_spacing_y(),
        True,  # auto_compact_left always on in browse mode
        owner.current_section_font_size(),
        owner.current_section_line_thickness(),
        owner.current_section_gap(),
        owner.current_section_line_color(),
        ctx.selected_ids,
        hidden_entry_ids_for_context(ctx),
        section_gap_above=owner.current_section_gap_above(),
        section_gap_below=owner.current_section_gap_below(),
        image_file_preview_enabled=owner.current_image_file_preview_enabled(),
        image_file_preview_mode=owner.current_image_file_preview_mode(),
        preview_overlay_enabled=owner.current_preview_overlay_enabled(),
        video_file_preview_enabled=owner.current_video_file_preview_enabled(),
        hover_preview_enabled=owner.current_hover_preview_enabled(),
        ffmpeg_manual_path=owner.current_ffmpeg_manual_path(),
        folder_show_file_count=owner.current_folder_show_file_count(),
        show_tooltips=owner.current_show_tooltips(),
        tile_font_size=(
            None
            if owner.current_tile_font_auto()
            else owner.current_tile_font_size()
        ),
    )
    owner._update_details(ctx)
    owner._update_action_buttons(ctx)
    return True


def _update_breadcrumb(ctx: ToolboxTabContext, visible: bool, path: Path | None = None) -> None:
    """Show/hide and update the breadcrumb bar for *ctx*."""
    bar = ctx.breadcrumb_bar
    if bar is None:
        return
    bar.setVisible(visible)
    if not visible or path is None:
        return
    # Update path label
    from PySide6 import QtWidgets
    label = bar.findChild(QtWidgets.QLabel, "lbl_breadcrumb_path")
    if label is not None:
        label.setText(str(path))
    # Update back button tooltip
    from PySide6 import QtWidgets as _QW  # noqa: F811
    btn = bar.findChild(_QW.QToolButton, "btn_browse_back")
    if btn is not None:
        parent_path = path.parent
        if ctx.browse_stack and len(ctx.browse_stack) > 1:
            btn.setToolTip(f"Zurück zu: {parent_path.name}")
        else:
            btn.setToolTip("Zurück zur Toolbox")
