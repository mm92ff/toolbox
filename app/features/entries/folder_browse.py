#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Folder-browsing logic for the toolbox canvas."""

from __future__ import annotations

import uuid
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from app import constants
from app.domain.models import ToolboxEntry
from app.domain.tab_context import ToolboxTabContext
from app.state.folder_browse_appearance import (
    FolderBrowseAppearanceStore,
    normalize_folder_path,
)


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
    if ctx.browse_stack and folder_icon_size_change_pending(ctx):
        commit_folder_icon_size_change(owner, ctx)
    ctx.browse_stack.append(folder)
    if not _refresh_browse_view(owner, ctx):
        ctx.browse_stack.pop()


def exit_folder_browse(owner: object, ctx: ToolboxTabContext) -> None:
    """Pop one level from the browse stack; restore normal view if stack is empty."""
    if ctx.browse_stack and folder_icon_size_change_pending(ctx):
        commit_folder_icon_size_change(owner, ctx)
    if ctx.browse_stack:
        ctx.browse_stack.pop()
    if ctx.browse_stack:
        if not _refresh_browse_view(owner, ctx):
            ctx.browse_stack.clear()
            ctx._browse_display_entries = []
            _update_breadcrumb(owner, ctx, visible=False)
            owner.refresh_canvas(ctx)
    else:
        # Back to normal
        ctx._browse_display_entries = []
        _update_breadcrumb(owner, ctx, visible=False)
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
    _update_breadcrumb(owner, ctx, visible=True, path=folder)

    from app.features.entries.controller_selection import hidden_entry_ids_for_context
    visible_ids = {entry.entry_id for entry in browse_entries}
    ctx.selected_ids = previous_selection & visible_ids
    ctx.canvas.set_entries(
        browse_entries,
        owner.icon_provider,
        effective_folder_icon_size(owner, folder),
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
        responsive_layout=True,
    )
    owner._update_details(ctx)
    owner._update_action_buttons(ctx)
    update_minimum_width = getattr(owner, "_update_window_minimum_width", None)
    if callable(update_minimum_width):
        update_minimum_width(ctx)
    return True


def _appearance_store(owner: object) -> FolderBrowseAppearanceStore | None:
    store = getattr(owner, "_folder_browse_appearance_store", None)
    return store if isinstance(store, FolderBrowseAppearanceStore) else None


def effective_folder_icon_size(owner: object, path: str | Path) -> int:
    """Return a folder override, falling back to the applied global size."""

    global_size = owner.current_icon_size()
    store = _appearance_store(owner)
    if store is None:
        try:
            return max(
                constants.MIN_ICON_SIZE,
                min(constants.MAX_ICON_SIZE, int(global_size)),
            )
        except (TypeError, ValueError, OverflowError):
            return constants.DEFAULT_ICON_SIZE
    return store.effective_icon_size(path, global_size)


def _sync_browse_size_controls(
    owner: object,
    ctx: ToolboxTabContext,
    path: str | Path,
) -> None:
    slider = ctx.browse_icon_size_slider
    value_label = ctx.browse_icon_size_value_label
    reset_button = ctx.browse_icon_size_reset_button
    size = effective_folder_icon_size(owner, path)
    store = _appearance_store(owner)
    has_override = store is not None and store.get_override(path) is not None
    if slider is not None:
        blocker = QtCore.QSignalBlocker(slider)
        slider.setValue(size)
        del blocker
    if value_label is not None:
        value_label.setText(f"{size} px")
    if reset_button is not None:
        reset_button.setEnabled(has_override)


def _apply_browse_layout(
    owner: object,
    ctx: ToolboxTabContext,
    icon_size: int | None = None,
) -> None:
    if not ctx.browse_stack:
        return
    size = icon_size or effective_folder_icon_size(owner, ctx.browse_stack[-1])
    ctx.canvas.apply_layout_settings(
        ctx._browse_display_entries,
        size,
        owner.current_tile_frame_enabled(),
        owner.current_tile_frame_thickness(),
        owner.current_tile_frame_color(),
        owner.current_tile_highlight_color(),
        owner.current_grid_spacing_x(),
        owner.current_grid_spacing_y(),
        True,
        owner.current_section_font_size(),
        owner.current_section_line_thickness(),
        owner.current_section_gap(),
        owner.current_section_line_color(),
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
            None if owner.current_tile_font_auto() else owner.current_tile_font_size()
        ),
        responsive_layout=True,
    )
    ctx.canvas.select_entries(ctx.selected_ids)
    owner._update_details(ctx)
    owner._update_action_buttons(ctx)
    update_minimum_width = getattr(owner, "_update_window_minimum_width", None)
    if callable(update_minimum_width):
        update_minimum_width(ctx)


def schedule_folder_icon_size_change(
    owner: object,
    ctx: ToolboxTabContext,
    value: int,
) -> None:
    """Update the readout immediately and debounce the heavier canvas update."""

    if not ctx.browse_stack:
        return
    if ctx.browse_icon_size_value_label is not None:
        ctx.browse_icon_size_value_label.setText(f"{int(value)} px")
    timer = ctx.browse_icon_size_timer
    if timer is None:
        apply_folder_icon_size_preview(owner, ctx)
    elif not timer.isActive():
        # Throttle expensive reflows while still updating during a long drag.
        timer.start()
    persist_timer = ctx.browse_icon_size_persist_timer
    if persist_timer is None:
        commit_folder_icon_size_change(owner, ctx)
    else:
        # Keyboard changes have no sliderReleased signal, so persist after idle.
        persist_timer.start()


def apply_folder_icon_size_preview(owner: object, ctx: ToolboxTabContext) -> None:
    """Apply the newest slider value in memory without writing settings to disk."""

    if not ctx.browse_stack or ctx.browse_icon_size_slider is None:
        return
    timer = ctx.browse_icon_size_timer
    if timer is not None:
        timer.stop()
    persist_timer = ctx.browse_icon_size_persist_timer
    restart_persist_debounce = bool(
        persist_timer is not None and persist_timer.isActive()
    )
    store = _appearance_store(owner)
    if store is None:
        return
    if store.set_icon_size(
        ctx.browse_stack[-1], ctx.browse_icon_size_slider.value()
    ):
        ctx._browse_icon_size_persist_pending = True
        if restart_persist_debounce and persist_timer is not None:
            # Count the idle interval after the potentially expensive visual reflow.
            persist_timer.start()


def commit_folder_icon_size_change(owner: object, ctx: ToolboxTabContext) -> None:
    """Commit the current slider value for the currently displayed folder."""

    if not ctx.browse_stack or ctx.browse_icon_size_slider is None:
        return
    timer = ctx.browse_icon_size_timer
    if timer is not None:
        timer.stop()
    persist_timer = ctx.browse_icon_size_persist_timer
    if persist_timer is not None:
        persist_timer.stop()
    path = ctx.browse_stack[-1]
    apply_folder_icon_size_preview(owner, ctx)
    if not ctx._browse_icon_size_persist_pending:
        return
    persist = getattr(owner, "_persist_folder_browse_settings", None)
    persisted = bool(persist()) if callable(persist) else False
    if not persisted:
        return
    ctx._browse_icon_size_persist_pending = False
    owner.status.showMessage(
        f"Symbolgröße für '{path.name or path}' gespeichert.", 2000
    )


def reset_folder_icon_size(owner: object, ctx: ToolboxTabContext) -> None:
    """Remove the current folder override and restore the global fallback."""

    if not ctx.browse_stack:
        return
    timer = ctx.browse_icon_size_timer
    if timer is not None:
        timer.stop()
    persist_timer = ctx.browse_icon_size_persist_timer
    if persist_timer is not None:
        persist_timer.stop()
    ctx._browse_icon_size_persist_pending = False
    store = _appearance_store(owner)
    path = ctx.browse_stack[-1]
    if store is None or not store.reset_icon_size(path):
        _sync_browse_size_controls(owner, ctx, path)
        _apply_browse_layout(owner, ctx)
        return
    persist = getattr(owner, "_persist_folder_browse_settings", None)
    if callable(persist):
        persist()
    owner.status.showMessage(
        "Ordner-Symbolgröße zurückgesetzt; globale Größe wird verwendet.", 2500
    )


def handle_folder_icon_size_store_change(
    owner: object,
    normalized_path: str,
    _size: object,
) -> None:
    """Refresh only open browse views which show the changed folder."""

    for ctx in owner.toolbox_tabs:
        if not ctx.browse_stack:
            continue
        if normalize_folder_path(ctx.browse_stack[-1]) != normalized_path:
            continue
        _sync_browse_size_controls(owner, ctx, ctx.browse_stack[-1])
        _apply_browse_layout(owner, ctx)


def flush_pending_folder_icon_size_changes(owner: object) -> None:
    """Commit debounced values before their tabs or window are destroyed."""

    for ctx in list(owner.toolbox_tabs):
        if folder_icon_size_change_pending(ctx):
            commit_folder_icon_size_change(owner, ctx)


def folder_icon_size_change_pending(ctx: ToolboxTabContext) -> bool:
    layout_timer_active = bool(
        ctx.browse_icon_size_timer is not None
        and ctx.browse_icon_size_timer.isActive()
    )
    persist_timer_active = bool(
        ctx.browse_icon_size_persist_timer is not None
        and ctx.browse_icon_size_persist_timer.isActive()
    )
    return bool(
        layout_timer_active
        or persist_timer_active
        or ctx._browse_icon_size_persist_pending
    )


def _update_breadcrumb(
    owner: object,
    ctx: ToolboxTabContext,
    visible: bool,
    path: Path | None = None,
) -> None:
    """Show/hide and update the breadcrumb bar for *ctx*."""
    bar = ctx.breadcrumb_bar
    if bar is None:
        return
    bar.setVisible(visible)
    if not visible or path is None:
        return
    label = ctx.browse_path_label or bar.findChild(
        QtWidgets.QLabel, constants.WIDGET_BROWSE_PATH_LABEL
    )
    if label is not None:
        label.setText(str(path))
        label.setToolTip(str(path))
    btn = bar.findChild(QtWidgets.QToolButton, constants.BUTTON_BROWSE_BACK)
    if btn is not None:
        parent_path = path.parent
        if ctx.browse_stack and len(ctx.browse_stack) > 1:
            btn.setToolTip(f"Zurück zu: {parent_path.name}")
        else:
            btn.setToolTip("Zurück zur Toolbox")
    _sync_browse_size_controls(owner, ctx, path)
