#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Selection/details helpers for entry interactions."""

from __future__ import annotations

import sys

from PySide6 import QtCore, QtWidgets

from app import constants
from app.domain.tab_context import ToolboxTabContext


def entries_for_current_view(ctx: ToolboxTabContext) -> list:
    if getattr(ctx, "browse_stack", None):
        return list(getattr(ctx, "_browse_display_entries", []))
    return list(ctx.entries)


def on_entry_clicked(owner: object, ctx: ToolboxTabContext, entry_id: str) -> None:
    from pathlib import Path
    modifiers = QtWidgets.QApplication.keyboardModifiers()
    shift_pressed = bool(modifiers & QtCore.Qt.KeyboardModifier.ShiftModifier)
    if shift_pressed:
        if entry_id in ctx.selected_ids:
            ctx.selected_ids.remove(entry_id)
        else:
            ctx.selected_ids.add(entry_id)
    else:
        ctx.selected_ids = {entry_id}
    apply_selection_only(owner, ctx)
    if shift_pressed:
        return

    entry = next(
        (item for item in entries_for_current_view(ctx) if item.entry_id == entry_id),
        None,
    )

    if entry is not None and entry.is_tool:
        path = Path(entry.path)
        # Folder single-click browse: enter folder on single click if setting enabled
        if (
            path.is_dir()
            and hasattr(owner, "current_folder_single_click_browse")
            and owner.current_folder_single_click_browse()
            and hasattr(owner, "_enter_folder_browse")
        ):
            owner._enter_folder_browse(ctx, path)
            return
        # Normal single-click tool launch
        if owner.current_tool_launch_mode() == constants.LAUNCH_CLICK_MODE_SINGLE:
            if not path.is_dir():
                owner._launch_entry(ctx, entry)



def on_canvas_background_clicked(owner: object, ctx: ToolboxTabContext) -> None:
    modifiers = QtWidgets.QApplication.keyboardModifiers()
    if modifiers & QtCore.Qt.KeyboardModifier.ShiftModifier:
        return
    if ctx.selected_ids:
        ctx.selected_ids.clear()
        apply_selection_only(owner, ctx)


def on_canvas_area_selection(
    owner: object,
    ctx: ToolboxTabContext,
    entry_ids: object,
    additive: bool,
) -> None:
    selected = {str(entry_id) for entry_id in entry_ids} if isinstance(entry_ids, (list, tuple, set)) else set()
    if additive:
        ctx.selected_ids.update(selected)
    else:
        ctx.selected_ids = selected
    apply_selection_only(owner, ctx)


def on_entry_activated(owner: object, ctx: ToolboxTabContext, entry_id: str) -> None:
    from pathlib import Path
    entry = next(
        (item for item in entries_for_current_view(ctx) if item.entry_id == entry_id),
        None,
    )
    if entry is None:
        return
    if entry.is_tool:
        path = Path(entry.path)
        if path.is_dir() and hasattr(owner, '_enter_folder_browse'):
            owner._enter_folder_browse(ctx, path)
            return
        if owner.current_tool_launch_mode() == constants.LAUNCH_CLICK_MODE_DOUBLE:
            owner._launch_entry(ctx, entry)
    else:
        owner._rename_entry(ctx, entry)


def on_entry_moved(owner: object, ctx: ToolboxTabContext, _entry_id: str, _x: int, _y: int) -> None:
    if ctx.canvas.responsive_layout_enabled():
        owner.status.showMessage(
            "Manuelles Verschieben ist im responsiven Layout deaktiviert.", 3000
        )
        return
    owner.persist_toolbox_state()
    update_details(owner, ctx)
    owner.status.showMessage("Position saved.", 1500)


def apply_selection_only(owner: object, ctx: ToolboxTabContext) -> None:
    ctx.canvas.select_entries(ctx.selected_ids)
    update_details(owner, ctx)
    update_action_buttons(ctx)


def update_action_buttons(ctx: ToolboxTabContext) -> None:
    selected_entries = [
        entry for entry in entries_for_current_view(ctx) if entry.entry_id in ctx.selected_ids
    ]
    has_selection = bool(selected_entries)
    has_tool = any(entry.is_tool for entry in selected_entries)
    ctx.launch_button.setEnabled(has_tool)
    ctx.remove_button.setEnabled(has_selection and not bool(ctx.browse_stack))


def update_details(owner: object, ctx: ToolboxTabContext) -> None:
    selected_entries = [
        entry for entry in entries_for_current_view(ctx) if entry.entry_id in ctx.selected_ids
    ]
    if not selected_entries:
        ctx.details_label.setText(
            "No selection yet. Drag files or folders into the toolbox or select an entry."
        )
        return
    if len(selected_entries) > 1:
        tools = sum(1 for entry in selected_entries if entry.is_tool)
        sections = len(selected_entries) - tools
        action_hint = "Browse view is read-only." if ctx.browse_stack else "Use Remove or Delete to clear the selection."
        ctx.details_label.setText(
            f"{len(selected_entries)} entries selected. Apps: {tools}, "
            f"section separators: {sections}. {action_hint}"
        )
        return
    entry = selected_entries[0]
    if entry.is_tool:
        admin_text = "Yes" if entry.always_run_as_admin else "No"
        persistent_options_text = "None"
        if owner._entry_has_persistent_launch_options(entry):
            args_text = entry.launch_arguments or "(none)"
            workdir_text = entry.launch_working_directory or "(default)"
            wait_text = "Yes" if entry.launch_wait else "No"
            persistent_options_text = (
                f"Arguments: {args_text}; Working directory: {workdir_text}; "
                f"Wait: {wait_text}"
            )
            if sys.platform == "win32":
                style_text = entry.launch_window_style or "normal"
                persistent_options_text += f"; Window style: {style_text}"
        admin_line = (
            f"Default launch as administrator: {admin_text}\n"
            if sys.platform == "win32"
            else ""
        )
        ctx.details_label.setText(
            f"{entry.title}\nPath: {entry.path}\n"
            f"{admin_line}Saved launch options: {persistent_options_text}"
        )
    else:
        ctx.details_label.setText(
            f"Section separator: {entry.title}\nDouble-click or right-click to rename."
        )


def hidden_entry_ids_for_context(ctx: ToolboxTabContext) -> set[str]:
    query_value = ctx.search_input.text()
    query = query_value.strip().lower() if isinstance(query_value, str) else ""
    if not query:
        return set()
    hidden_ids: set[str] = set()
    for entry in entries_for_current_view(ctx):
        haystack = (entry.custom_title or entry.title).lower()
        if entry.is_tool:
            haystack += f"\n{entry.path.lower()}"
        if query not in haystack:
            hidden_ids.add(entry.entry_id)
    return hidden_ids
