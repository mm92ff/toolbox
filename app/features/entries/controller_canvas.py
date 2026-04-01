#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canvas refresh and config-opening helpers for entries controller."""

from __future__ import annotations

from typing import Optional

from PySide6 import QtWidgets

from app.domain.tab_context import ToolboxTabContext
from app.features.entries.controller_selection import (
    hidden_entry_ids_for_context,
    update_action_buttons,
    update_details,
)
from app.services.system_utils import open_directory_in_os


def refresh_canvas(owner: object, ctx: Optional[ToolboxTabContext] = None) -> None:
    ctx = ctx or owner.current_toolbox_context()
    if ctx is None:
        return
    ctx.canvas.set_entries(
        ctx.entries,
        owner.icon_provider,
        owner.current_icon_size(),
        owner.current_tile_frame_enabled(),
        owner.current_tile_frame_thickness(),
        owner.current_tile_frame_color(),
        owner.current_tile_highlight_color(),
        owner.current_grid_spacing_x(),
        owner.current_grid_spacing_y(),
        owner.current_auto_compact_left(),
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
        video_file_preview_enabled=owner.current_video_file_preview_enabled(),
        hover_preview_enabled=owner.current_hover_preview_enabled(),
    )
    update_details(owner, ctx)
    update_action_buttons(ctx)
    update_window_minimum_width(owner, ctx)


def refresh_all_canvases(owner: object, apply_layout_only: bool = False) -> None:
    layout_reflow_changed_entries = False
    for ctx in owner.toolbox_tabs:
        if apply_layout_only and ctx.canvas.surface._widgets:
            reflow_changed = ctx.canvas.apply_layout_settings(
                ctx.entries,
                owner.current_icon_size(),
                owner.current_tile_frame_enabled(),
                owner.current_tile_frame_thickness(),
                owner.current_tile_frame_color(),
                owner.current_tile_highlight_color(),
                owner.current_grid_spacing_x(),
                owner.current_grid_spacing_y(),
                owner.current_auto_compact_left(),
                owner.current_section_font_size(),
                owner.current_section_line_thickness(),
                owner.current_section_gap(),
                owner.current_section_line_color(),
                section_gap_above=owner.current_section_gap_above(),
                section_gap_below=owner.current_section_gap_below(),
                image_file_preview_enabled=owner.current_image_file_preview_enabled(),
                image_file_preview_mode=owner.current_image_file_preview_mode(),
                video_file_preview_enabled=owner.current_video_file_preview_enabled(),
                hover_preview_enabled=owner.current_hover_preview_enabled(),
            )
            if reflow_changed:
                layout_reflow_changed_entries = True
            ctx.canvas.select_entries(ctx.selected_ids)
            hidden_entry_ids = hidden_entry_ids_for_context(ctx)
            for entry_id, widget in ctx.canvas.surface._widgets.items():
                widget.setVisible(entry_id not in hidden_entry_ids)
            ctx.canvas.surface._update_canvas_size()
            update_details(owner, ctx)
            update_action_buttons(ctx)
        else:
            refresh_canvas(owner, ctx)
    if layout_reflow_changed_entries:
        owner.persist_toolbox_state()
    owner._update_tile_color_previews()
    owner._update_section_color_preview()
    owner._refresh_section_color_manager()
    update_window_minimum_width(owner, owner.current_toolbox_context())


def update_window_minimum_width(owner: object, _ctx: Optional[ToolboxTabContext]) -> None:
    base_min_width = owner.minimumSizeHint().width()
    owner.setMinimumWidth(base_min_width)


def open_config_directory(owner: object) -> None:
    if open_directory_in_os(str(owner.config_dir)):
        owner.status.showMessage(f"Config folder opened: {owner.config_dir}", 3000)
    else:
        QtWidgets.QMessageBox.warning(owner, "Error", f"Could not open folder:\n{owner.config_dir}")

