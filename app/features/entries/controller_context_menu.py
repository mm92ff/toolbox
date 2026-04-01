#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Context menu helpers for entry and canvas interactions."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from app.domain.tab_context import ToolboxTabContext
from app.features.entries.controller_crud import add_section, remove_selected, rename_entry


def show_canvas_context_menu(
    owner: object,
    ctx: ToolboxTabContext,
    entry_id: str,
    global_pos: QtCore.QPoint,
) -> None:
    entry = next((item for item in ctx.entries if item.entry_id == entry_id), None)
    if entry is None:
        return
    if entry_id not in ctx.selected_ids:
        ctx.selected_ids = {entry_id}
        owner._apply_selection_only(ctx)

    menu = QtWidgets.QMenu(owner)
    if entry.is_tool:
        start_action = menu.addAction("Launch")
        start_with_options_action = menu.addAction("Launch with Parameters ...")
        admin_now_action = menu.addAction("Run as Administrator")
        menu.addSeparator()
        persistent_admin_action = menu.addAction("Always Run as Administrator")
        persistent_admin_action.setCheckable(True)
        persistent_admin_action.setChecked(entry.always_run_as_admin)
        save_persistent_options_action = menu.addAction("Save Default Launch Options ...")
        clear_persistent_options_action = menu.addAction("Reset Default Launch Options")
        clear_persistent_options_action.setEnabled(owner._entry_has_persistent_launch_options(entry))
        menu.addSeparator()
        open_path_action = menu.addAction("Open Path")
        rename_action = menu.addAction("Rename")
        remove_action = menu.addAction("Remove Selected" if len(ctx.selected_ids) > 1 else "Remove")
        chosen = menu.exec(global_pos)
        if chosen == start_action:
            owner._launch_entry(ctx, entry)
        elif chosen == start_with_options_action:
            owner._launch_entry_with_options(ctx, entry)
        elif chosen == admin_now_action:
            owner._launch_entry(ctx, entry, force_admin=True)
        elif chosen == persistent_admin_action:
            entry.always_run_as_admin = persistent_admin_action.isChecked()
            owner.persist_toolbox_state()
            owner._update_details(ctx)
            admin_status = "Enabled" if entry.always_run_as_admin else "Disabled"
            owner.status.showMessage(
                f"{admin_status}: Always run as administrator for {entry.title}",
                3000,
            )
        elif chosen == save_persistent_options_action:
            owner._configure_persistent_launch_options(ctx, entry)
        elif chosen == clear_persistent_options_action:
            owner._clear_persistent_launch_options(ctx, entry)
        elif chosen == open_path_action:
            owner._open_entry_path(entry)
        elif chosen == rename_action:
            rename_entry(owner, ctx, entry)
        elif chosen == remove_action:
            remove_selected(owner, ctx)
        return

    rename_action = menu.addAction("Rename Header")
    remove_action = menu.addAction("Remove")
    chosen = menu.exec(global_pos)
    if chosen == rename_action:
        rename_entry(owner, ctx, entry)
    elif chosen == remove_action:
        remove_selected(owner, ctx)


def set_toolbox_tab_background_color(owner: object, ctx: ToolboxTabContext, color_value: str) -> None:
    normalized = owner._normalize_tab_background_color(color_value)
    if normalized == ctx.background_color:
        return
    ctx.background_color = normalized
    owner._apply_tab_background_color(ctx)
    owner.persist_toolbox_state()
    if normalized:
        owner.status.showMessage(f"Background color saved for tab '{ctx.title}'.", 2500)
    else:
        owner.status.showMessage(f"Background color reset for tab '{ctx.title}'.", 2500)


def show_canvas_background_context_menu(
    owner: object,
    ctx: ToolboxTabContext,
    canvas_pos: QtCore.QPoint,
    global_pos: QtCore.QPoint,
) -> None:
    menu = QtWidgets.QMenu(owner)
    add_section_action = menu.addAction("Add Section")
    menu.addSeparator()
    insert_below_action = menu.addAction("Insert Row Below")
    insert_above_action = menu.addAction("Insert Row Above")
    menu.addSeparator()
    set_tab_background_action = menu.addAction("Set Tab Background Color...")
    reset_tab_background_action = menu.addAction("Reset Tab Background Color")
    reset_tab_background_action.setEnabled(bool(ctx.background_color.strip()))
    chosen = menu.exec(global_pos)
    if chosen == add_section_action:
        add_section(owner, ctx, preferred_y=canvas_pos.y())
    elif chosen == insert_below_action:
        shifted = ctx.canvas.insert_tool_row(ctx.entries, canvas_pos.y(), below=True)
        owner.persist_toolbox_state()
        owner.refresh_canvas(ctx)
        owner.status.showMessage(
            f"Inserted row below ({shifted} entries moved)." if shifted else "Inserted row below.",
            2500,
        )
    elif chosen == insert_above_action:
        shifted = ctx.canvas.insert_tool_row(ctx.entries, canvas_pos.y(), below=False)
        owner.persist_toolbox_state()
        owner.refresh_canvas(ctx)
        owner.status.showMessage(
            f"Inserted row above ({shifted} entries moved)." if shifted else "Inserted row above.",
            2500,
        )
    elif chosen == set_tab_background_action:
        initial_color = QtGui.QColor(ctx.background_color.strip())
        if not initial_color.isValid():
            initial_color = owner.palette().color(QtGui.QPalette.ColorRole.Base)
        selected_color = QtWidgets.QColorDialog.getColor(
            initial_color,
            owner,
            f"Tab Background Color - {ctx.title}",
        )
        if selected_color.isValid():
            set_toolbox_tab_background_color(owner, ctx, selected_color.name())
    elif chosen == reset_tab_background_action:
        set_toolbox_tab_background_color(owner, ctx, "")

