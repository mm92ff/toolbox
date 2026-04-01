#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Selection/details helpers for entry interactions."""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from app import constants
from app.domain.tab_context import ToolboxTabContext


def on_entry_clicked(owner: object, ctx: ToolboxTabContext, entry_id: str) -> None:
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
    if shift_pressed or owner.current_tool_launch_mode() != constants.LAUNCH_CLICK_MODE_SINGLE:
        return

    entry = next((item for item in ctx.entries if item.entry_id == entry_id), None)
    if entry is not None and entry.is_tool:
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
    entry = next((item for item in ctx.entries if item.entry_id == entry_id), None)
    if entry is None:
        return
    if entry.is_tool:
        if owner.current_tool_launch_mode() == constants.LAUNCH_CLICK_MODE_DOUBLE:
            owner._launch_entry(ctx, entry)
    else:
        owner._rename_entry(ctx, entry)


def on_entry_moved(owner: object, ctx: ToolboxTabContext, _entry_id: str, _x: int, _y: int) -> None:
    owner.persist_toolbox_state()
    update_details(owner, ctx)
    owner.status.showMessage("Position saved.", 1500)


def apply_selection_only(owner: object, ctx: ToolboxTabContext) -> None:
    ctx.canvas.select_entries(ctx.selected_ids)
    update_details(owner, ctx)
    update_action_buttons(ctx)


def update_action_buttons(ctx: ToolboxTabContext) -> None:
    selected_entries = [entry for entry in ctx.entries if entry.entry_id in ctx.selected_ids]
    has_selection = bool(selected_entries)
    has_tool = any(entry.is_tool for entry in selected_entries)
    ctx.launch_button.setEnabled(has_tool)
    ctx.remove_button.setEnabled(has_selection)


def update_details(owner: object, ctx: ToolboxTabContext) -> None:
    selected_entries = [entry for entry in ctx.entries if entry.entry_id in ctx.selected_ids]
    if not selected_entries:
        ctx.details_label.setText(
            "No selection yet. Drag files or folders into the toolbox or select an entry."
        )
        return
    if len(selected_entries) > 1:
        tools = sum(1 for entry in selected_entries if entry.is_tool)
        sections = len(selected_entries) - tools
        ctx.details_label.setText(
            (
                f"{len(selected_entries)} entries selected. Apps: {tools}, "
                f"section separators: {sections}. "
                "Use Remove or Delete to clear the selection."
            )
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
            style_text = entry.launch_window_style or "normal"
            persistent_options_text = (
                f"Arguments: {args_text}; Working directory: {workdir_text}; "
                f"Wait: {wait_text}; Window style: {style_text}"
            )
        ctx.details_label.setText(
            (
                f"{entry.title}\nPath: {entry.path}\n"
                f"Default launch as administrator: {admin_text}\n"
                f"Saved launch options: {persistent_options_text}"
            )
        )
    else:
        ctx.details_label.setText(
            f"Section separator: {entry.title}\nDouble-click or right-click to rename."
        )


def hidden_entry_ids_for_context(ctx: ToolboxTabContext) -> set[str]:
    query = ctx.search_input.text().strip().lower()
    if not query:
        return set()
    hidden_ids: set[str] = set()
    for entry in ctx.entries:
        haystack = entry.title.lower()
        if entry.is_tool:
            haystack += f"\n{entry.path.lower()}"
        if query not in haystack:
            hidden_ids.add(entry.entry_id)
    return hidden_ids

