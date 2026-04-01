#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entry and canvas interaction behavior split out from MainWindow."""

from __future__ import annotations

from typing import Optional

from PySide6 import QtCore

from app.domain.models import ToolboxEntry
from app.domain.tab_context import ToolboxTabContext
from app.features.entries.controller_canvas import (
    open_config_directory,
    refresh_all_canvases,
    refresh_canvas,
    update_window_minimum_width,
)
from app.features.entries.controller_context_menu import (
    set_toolbox_tab_background_color,
    show_canvas_background_context_menu,
    show_canvas_context_menu,
)
from app.features.entries.controller_crud import (
    add_section,
    add_tool_paths,
    add_tools_from_dialog,
    extract_supported_paths,
    path_log_label,
    remove_selected,
    rename_entry,
)
from app.features.entries.controller_selection import (
    apply_selection_only,
    hidden_entry_ids_for_context,
    on_canvas_area_selection,
    on_canvas_background_clicked,
    on_entry_activated,
    on_entry_clicked,
    on_entry_moved,
    update_action_buttons,
    update_details,
)
from app.features.entries.diagnostics import MainWindowEntryDiagnosticsMixin
from app.features.entries.launching import MainWindowEntryLaunchingMixin


class MainWindowEntriesMixin(MainWindowEntryLaunchingMixin, MainWindowEntryDiagnosticsMixin):
    @staticmethod
    def _path_log_label(raw_path: str) -> str:
        return path_log_label(raw_path)

    def _mime_contains_supported_paths(self, mime_data: QtCore.QMimeData) -> bool:
        return bool(extract_supported_paths(mime_data))

    def _extract_supported_paths(self, mime_data: QtCore.QMimeData) -> list[str]:
        return extract_supported_paths(mime_data)

    def add_tools_from_dialog(self, ctx: Optional[ToolboxTabContext] = None) -> None:
        add_tools_from_dialog(self, ctx)

    def add_tool_paths(self, ctx: ToolboxTabContext, paths: list[str]) -> None:
        add_tool_paths(self, ctx, paths)

    def add_section(
        self,
        ctx: Optional[ToolboxTabContext] = None,
        preferred_y: Optional[int] = None,
    ) -> None:
        add_section(self, ctx, preferred_y)

    def remove_selected(self, ctx: Optional[ToolboxTabContext] = None) -> None:
        remove_selected(self, ctx)

    def _rename_entry(self, ctx: ToolboxTabContext, entry: ToolboxEntry) -> None:
        rename_entry(self, ctx, entry)

    def _show_canvas_context_menu(
        self, ctx: ToolboxTabContext, entry_id: str, global_pos: QtCore.QPoint
    ) -> None:
        show_canvas_context_menu(self, ctx, entry_id, global_pos)

    def _on_entry_clicked(self, ctx: ToolboxTabContext, entry_id: str) -> None:
        on_entry_clicked(self, ctx, entry_id)

    def _on_canvas_background_clicked(self, ctx: ToolboxTabContext) -> None:
        on_canvas_background_clicked(self, ctx)

    def _on_canvas_area_selection(
        self, ctx: ToolboxTabContext, entry_ids: object, additive: bool
    ) -> None:
        on_canvas_area_selection(self, ctx, entry_ids, additive)

    def _show_canvas_background_context_menu(
        self,
        ctx: ToolboxTabContext,
        canvas_pos: QtCore.QPoint,
        global_pos: QtCore.QPoint,
    ) -> None:
        show_canvas_background_context_menu(self, ctx, canvas_pos, global_pos)

    def _set_toolbox_tab_background_color(self, ctx: ToolboxTabContext, color_value: str) -> None:
        set_toolbox_tab_background_color(self, ctx, color_value)

    def _on_entry_activated(self, ctx: ToolboxTabContext, entry_id: str) -> None:
        on_entry_activated(self, ctx, entry_id)

    def _on_entry_moved(self, ctx: ToolboxTabContext, entry_id: str, x: int, y: int) -> None:
        on_entry_moved(self, ctx, entry_id, x, y)

    def _apply_selection_only(self, ctx: ToolboxTabContext) -> None:
        apply_selection_only(self, ctx)

    def _update_action_buttons(self, ctx: ToolboxTabContext) -> None:
        update_action_buttons(ctx)

    def _update_details(self, ctx: ToolboxTabContext) -> None:
        update_details(self, ctx)

    def _hidden_entry_ids_for_context(self, ctx: ToolboxTabContext) -> set[str]:
        return hidden_entry_ids_for_context(ctx)

    def refresh_canvas(self, ctx: Optional[ToolboxTabContext] = None) -> None:
        refresh_canvas(self, ctx)

    def refresh_all_canvases(self, apply_layout_only: bool = False) -> None:
        refresh_all_canvases(self, apply_layout_only=apply_layout_only)

    def _update_window_minimum_width(self, ctx: Optional[ToolboxTabContext]) -> None:
        update_window_minimum_width(self, ctx)

    def _open_config_directory(self) -> None:
        open_config_directory(self)

