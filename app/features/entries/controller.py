#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entry and canvas interaction behavior split out from MainWindow."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtWidgets

from app import constants
from app.domain.models import ToolboxEntry
from app.domain.tab_context import ToolboxTabContext
from app.features.entries.diagnostics import MainWindowEntryDiagnosticsMixin
from app.features.entries.launching import MainWindowEntryLaunchingMixin
from app.services.paths import resolve_supported_tool_path
from app.services.system_utils import (
    display_name_from_path,
    normalize_tool_path,
    open_directory_in_os,
)

logger = logging.getLogger(__name__)


class MainWindowEntriesMixin(MainWindowEntryLaunchingMixin, MainWindowEntryDiagnosticsMixin):
    @staticmethod
    def _path_log_label(raw_path: str) -> str:
        path = Path(raw_path).expanduser()
        label = path.name.strip()
        return label or str(path)

    def _mime_contains_supported_paths(self, mime_data: QtCore.QMimeData) -> bool:
        return bool(self._extract_supported_paths(mime_data))

    def _extract_supported_paths(self, mime_data: QtCore.QMimeData) -> list[str]:
        supported: list[str] = []
        for url in mime_data.urls():
            local_path = url.toLocalFile()
            if not local_path:
                continue
            resolved = resolve_supported_tool_path(local_path)
            if resolved is not None:
                supported.append(str(resolved))
        return supported

    def add_tools_from_dialog(self, ctx: Optional[ToolboxTabContext] = None) -> None:
        ctx = ctx or self.current_toolbox_context()
        if ctx is None:
            return
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, "Add Apps", str(Path.home()), constants.TOOL_FILE_FILTER
        )
        if files:
            self.add_tool_paths(ctx, files)

    def add_tool_paths(self, ctx: ToolboxTabContext, paths: list[str]) -> None:
        known_paths = {normalize_tool_path(entry.path) for entry in ctx.entries if entry.is_tool}
        added = 0
        skipped_invalid = 0
        for raw_path in paths:
            resolved = resolve_supported_tool_path(raw_path)
            if resolved is None:
                skipped_invalid += 1
                logger.warning(
                    "Skipping unsupported or missing tool path: %s",
                    self._path_log_label(raw_path),
                )
                continue
            normalized = normalize_tool_path(str(resolved))
            if normalized in known_paths:
                continue
            x, y = ctx.canvas.find_next_free_tool_position(ctx.entries)
            ctx.entries.append(
                ToolboxEntry(
                    title=display_name_from_path(str(resolved)),
                    kind=constants.ENTRY_KIND_TOOL,
                    path=str(resolved),
                    x=x,
                    y=y,
                )
            )
            known_paths.add(normalized)
            added += 1
        if added and skipped_invalid:
            self.persist_toolbox_state()
            self.refresh_canvas(ctx)
            self.status.showMessage(
                f"{added} entry/entries added, {skipped_invalid} invalid skipped.", 3500
            )
        elif added:
            self.persist_toolbox_state()
            self.refresh_canvas(ctx)
            self.status.showMessage(f"{added} entry/entries added.", 3000)
        elif skipped_invalid:
            self.status.showMessage("No entries added (invalid paths).", 3000)
        else:
            self.status.showMessage("No new entries added.", 3000)

    def add_section(
        self,
        ctx: Optional[ToolboxTabContext] = None,
        preferred_y: Optional[int] = None,
    ) -> None:
        ctx = ctx or self.current_toolbox_context()
        if ctx is None:
            return
        title, accepted = QtWidgets.QInputDialog.getText(self, "Add Section", "Header:")
        title = title.strip()
        if not accepted or not title:
            return
        if preferred_y is None:
            section_y = ctx.canvas.find_next_section_y(ctx.entries)
        else:
            section_y = ctx.canvas.snap_section_y(ctx.entries, preferred_y)
        ctx.entries.append(
            ToolboxEntry(
                title=title,
                kind=constants.ENTRY_KIND_SECTION,
                x=constants.CANVAS_PADDING,
                y=section_y,
            )
        )
        self.persist_toolbox_state()
        self.refresh_canvas(ctx)
        self.status.showMessage("Section added.", 3000)

    def remove_selected(self, ctx: Optional[ToolboxTabContext] = None) -> None:
        ctx = ctx or self.current_toolbox_context()
        if ctx is None or not ctx.selected_ids:
            return
        count = len(ctx.selected_ids)
        removed_tools = any(
            entry.entry_id in ctx.selected_ids and entry.is_tool for entry in ctx.entries
        )
        ctx.entries = [entry for entry in ctx.entries if entry.entry_id not in ctx.selected_ids]
        ctx.selected_ids.clear()
        if removed_tools and self.current_auto_compact_left():
            ctx.canvas.compact_tools(ctx.entries)
        self.persist_toolbox_state()
        self.refresh_canvas(ctx)
        self.status.showMessage(f"{count} entry/entries removed.", 3000)

    def _rename_entry(self, ctx: ToolboxTabContext, entry: ToolboxEntry) -> None:
        title, accepted = QtWidgets.QInputDialog.getText(
            self, "Rename Entry", "Name:", text=entry.title
        )
        title = title.strip()
        if not accepted or not title:
            return
        entry.title = title
        self.persist_toolbox_state()
        self.refresh_canvas(ctx)

    def _show_canvas_context_menu(
        self, ctx: ToolboxTabContext, entry_id: str, global_pos: QtCore.QPoint
    ) -> None:
        entry = next((item for item in ctx.entries if item.entry_id == entry_id), None)
        if entry is None:
            return
        if entry_id not in ctx.selected_ids:
            ctx.selected_ids = {entry_id}
            self._apply_selection_only(ctx)

        menu = QtWidgets.QMenu(self)
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
            clear_persistent_options_action.setEnabled(
                self._entry_has_persistent_launch_options(entry)
            )
            menu.addSeparator()
            open_path_action = menu.addAction("Open Path")
            rename_action = menu.addAction("Rename")
            remove_action = menu.addAction(
                "Remove Selected" if len(ctx.selected_ids) > 1 else "Remove"
            )
            chosen = menu.exec(global_pos)
            if chosen == start_action:
                self._launch_entry(ctx, entry)
            elif chosen == start_with_options_action:
                self._launch_entry_with_options(ctx, entry)
            elif chosen == admin_now_action:
                self._launch_entry(ctx, entry, force_admin=True)
            elif chosen == persistent_admin_action:
                entry.always_run_as_admin = persistent_admin_action.isChecked()
                self.persist_toolbox_state()
                self._update_details(ctx)
                admin_status = "Enabled" if entry.always_run_as_admin else "Disabled"
                self.status.showMessage(
                    f"{admin_status}: Always run as administrator for {entry.title}",
                    3000,
                )
            elif chosen == save_persistent_options_action:
                self._configure_persistent_launch_options(ctx, entry)
            elif chosen == clear_persistent_options_action:
                self._clear_persistent_launch_options(ctx, entry)
            elif chosen == open_path_action:
                self._open_entry_path(entry)
            elif chosen == rename_action:
                self._rename_entry(ctx, entry)
            elif chosen == remove_action:
                self.remove_selected(ctx)
            return

        rename_action = menu.addAction("Rename Header")
        remove_action = menu.addAction("Remove")
        chosen = menu.exec(global_pos)
        if chosen == rename_action:
            self._rename_entry(ctx, entry)
        elif chosen == remove_action:
            self.remove_selected(ctx)

    def _on_entry_clicked(self, ctx: ToolboxTabContext, entry_id: str) -> None:
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        shift_pressed = bool(modifiers & QtCore.Qt.KeyboardModifier.ShiftModifier)
        if shift_pressed:
            if entry_id in ctx.selected_ids:
                ctx.selected_ids.remove(entry_id)
            else:
                ctx.selected_ids.add(entry_id)
        else:
            ctx.selected_ids = {entry_id}
        self._apply_selection_only(ctx)
        if shift_pressed or self.current_tool_launch_mode() != constants.LAUNCH_CLICK_MODE_SINGLE:
            return

        entry = next((item for item in ctx.entries if item.entry_id == entry_id), None)
        if entry is not None and entry.is_tool:
            self._launch_entry(ctx, entry)

    def _on_canvas_background_clicked(self, ctx: ToolboxTabContext) -> None:
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers & QtCore.Qt.KeyboardModifier.ShiftModifier:
            return
        if ctx.selected_ids:
            ctx.selected_ids.clear()
            self._apply_selection_only(ctx)

    def _on_canvas_area_selection(
        self, ctx: ToolboxTabContext, entry_ids: object, additive: bool
    ) -> None:
        selected = (
            {str(entry_id) for entry_id in entry_ids}
            if isinstance(entry_ids, (list, tuple, set))
            else set()
        )
        if additive:
            ctx.selected_ids.update(selected)
        else:
            ctx.selected_ids = selected
        self._apply_selection_only(ctx)

    def _show_canvas_background_context_menu(
        self,
        ctx: ToolboxTabContext,
        canvas_pos: QtCore.QPoint,
        global_pos: QtCore.QPoint,
    ) -> None:
        menu = QtWidgets.QMenu(self)
        add_section_action = menu.addAction("Add Section")
        menu.addSeparator()
        insert_below_action = menu.addAction("Insert Row Below")
        insert_above_action = menu.addAction("Insert Row Above")
        chosen = menu.exec(global_pos)
        if chosen == add_section_action:
            self.add_section(ctx, preferred_y=canvas_pos.y())
        elif chosen == insert_below_action:
            shifted = ctx.canvas.insert_tool_row(ctx.entries, canvas_pos.y(), below=True)
            self.persist_toolbox_state()
            self.refresh_canvas(ctx)
            self.status.showMessage(
                (
                    f"Inserted row below ({shifted} entries moved)."
                    if shifted
                    else "Inserted row below."
                ),
                2500,
            )
        elif chosen == insert_above_action:
            shifted = ctx.canvas.insert_tool_row(ctx.entries, canvas_pos.y(), below=False)
            self.persist_toolbox_state()
            self.refresh_canvas(ctx)
            self.status.showMessage(
                (
                    f"Inserted row above ({shifted} entries moved)."
                    if shifted
                    else "Inserted row above."
                ),
                2500,
            )

    def _on_entry_activated(self, ctx: ToolboxTabContext, entry_id: str) -> None:
        entry = next((item for item in ctx.entries if item.entry_id == entry_id), None)
        if entry is None:
            return
        if entry.is_tool:
            if self.current_tool_launch_mode() == constants.LAUNCH_CLICK_MODE_DOUBLE:
                self._launch_entry(ctx, entry)
        else:
            self._rename_entry(ctx, entry)

    def _on_entry_moved(self, ctx: ToolboxTabContext, entry_id: str, x: int, y: int) -> None:
        self.persist_toolbox_state()
        self._update_details(ctx)
        self.status.showMessage("Position saved.", 1500)

    def _apply_selection_only(self, ctx: ToolboxTabContext) -> None:
        ctx.canvas.select_entries(ctx.selected_ids)
        self._update_details(ctx)
        self._update_action_buttons(ctx)

    def _update_action_buttons(self, ctx: ToolboxTabContext) -> None:
        selected_entries = [entry for entry in ctx.entries if entry.entry_id in ctx.selected_ids]
        has_selection = bool(selected_entries)
        has_tool = any(entry.is_tool for entry in selected_entries)
        ctx.launch_button.setEnabled(has_tool)
        ctx.remove_button.setEnabled(has_selection)

    def _update_details(self, ctx: ToolboxTabContext) -> None:
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
            if self._entry_has_persistent_launch_options(entry):
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

    def _hidden_entry_ids_for_context(self, ctx: ToolboxTabContext) -> set[str]:
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

    def refresh_canvas(self, ctx: Optional[ToolboxTabContext] = None) -> None:
        ctx = ctx or self.current_toolbox_context()
        if ctx is None:
            return
        ctx.canvas.set_entries(
            ctx.entries,
            self.icon_provider,
            self.current_icon_size(),
            self.current_tile_frame_enabled(),
            self.current_tile_frame_thickness(),
            self.current_tile_frame_color(),
            self.current_tile_highlight_color(),
            self.current_grid_spacing_x(),
            self.current_grid_spacing_y(),
            self.current_auto_compact_left(),
            self.current_section_font_size(),
            self.current_section_line_thickness(),
            self.current_section_gap(),
            self.current_section_line_color(),
            ctx.selected_ids,
            self._hidden_entry_ids_for_context(ctx),
            section_gap_above=self.current_section_gap_above(),
            section_gap_below=self.current_section_gap_below(),
        )
        self._update_details(ctx)
        self._update_action_buttons(ctx)
        self._update_window_minimum_width(ctx)

    def refresh_all_canvases(self, apply_layout_only: bool = False) -> None:
        layout_reflow_changed_entries = False
        for ctx in self.toolbox_tabs:
            if apply_layout_only and ctx.canvas.surface._widgets:
                reflow_changed = ctx.canvas.apply_layout_settings(
                    ctx.entries,
                    self.current_icon_size(),
                    self.current_tile_frame_enabled(),
                    self.current_tile_frame_thickness(),
                    self.current_tile_frame_color(),
                    self.current_tile_highlight_color(),
                    self.current_grid_spacing_x(),
                    self.current_grid_spacing_y(),
                    self.current_auto_compact_left(),
                    self.current_section_font_size(),
                    self.current_section_line_thickness(),
                    self.current_section_gap(),
                    self.current_section_line_color(),
                    section_gap_above=self.current_section_gap_above(),
                    section_gap_below=self.current_section_gap_below(),
                )
                if reflow_changed:
                    layout_reflow_changed_entries = True
                ctx.canvas.select_entries(ctx.selected_ids)
                hidden_entry_ids = self._hidden_entry_ids_for_context(ctx)
                for entry_id, widget in ctx.canvas.surface._widgets.items():
                    widget.setVisible(entry_id not in hidden_entry_ids)
                ctx.canvas.surface._update_canvas_size()
                self._update_details(ctx)
                self._update_action_buttons(ctx)
            else:
                self.refresh_canvas(ctx)
        if layout_reflow_changed_entries:
            self.persist_toolbox_state()
        self._update_tile_color_previews()
        self._update_section_color_preview()
        self._refresh_section_color_manager()
        self._update_window_minimum_width(self.current_toolbox_context())

    def _update_window_minimum_width(self, ctx: Optional[ToolboxTabContext]) -> None:
        base_min_width = self.minimumSizeHint().width()
        self.setMinimumWidth(base_min_width)

    def _open_config_directory(self) -> None:
        if open_directory_in_os(str(self.config_dir)):
            self.status.showMessage(f"Config folder opened: {self.config_dir}", 3000)
        else:
            QtWidgets.QMessageBox.warning(
                self, "Error", f"Could not open folder:\n{self.config_dir}"
            )
