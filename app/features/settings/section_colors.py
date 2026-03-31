#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Section color manager logic for per-section and global overrides."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from app import constants
from app.domain.models import ToolboxEntry
from app.domain.tab_context import ToolboxTabContext


class MainWindowSettingsSectionColorsMixin:
    @staticmethod
    def _normalize_optional_section_color(value: str) -> str | None:
        text = (value or "").strip()
        if text.lower() in {"", "default", "inherit", "theme"}:
            return ""
        color = QtGui.QColor(text)
        if not color.isValid():
            return None
        return color.name()

    @staticmethod
    def _display_optional_section_color(value: str) -> str:
        normalized = (value or "").strip()
        return normalized if normalized else "(default)"

    def _iter_all_sections(self) -> list[tuple[ToolboxTabContext, ToolboxEntry]]:
        items: list[tuple[ToolboxTabContext, ToolboxEntry]] = []
        for ctx in self.toolbox_tabs:
            for entry in ctx.entries:
                if entry.is_section:
                    items.append((ctx, entry))
        return items

    def _find_section_entry(
        self, tab_id: str, entry_id: str
    ) -> tuple[ToolboxTabContext, ToolboxEntry] | None:
        for ctx in self.toolbox_tabs:
            if ctx.tab_id != tab_id:
                continue
            for entry in ctx.entries:
                if entry.entry_id == entry_id and entry.is_section:
                    return ctx, entry
        return None

    def _selected_section_entry(self) -> tuple[ToolboxTabContext, ToolboxEntry] | None:
        list_widget = self.widgets[constants.WIDGET_SECTION_COLOR_LIST]
        if not isinstance(list_widget, QtWidgets.QListWidget):
            return None
        item = list_widget.currentItem()
        if item is None:
            return None
        payload = item.data(QtCore.Qt.ItemDataRole.UserRole)
        if not isinstance(payload, tuple) or len(payload) != 2:
            return None
        tab_id, entry_id = payload
        if not isinstance(tab_id, str) or not isinstance(entry_id, str):
            return None
        return self._find_section_entry(tab_id, entry_id)

    def _set_selected_section_controls_enabled(self, enabled: bool) -> None:
        for widget_name in (
            constants.WIDGET_SECTION_SELECTED_LINE_COLOR_INPUT,
            constants.WIDGET_SECTION_SELECTED_LINE_COLOR_BUTTON,
            constants.BUTTON_SECTION_APPLY_SELECTED_LINE_COLOR,
            constants.WIDGET_SECTION_SELECTED_TITLE_COLOR_INPUT,
            constants.WIDGET_SECTION_SELECTED_TITLE_COLOR_BUTTON,
            constants.BUTTON_SECTION_APPLY_SELECTED_TITLE_COLOR,
        ):
            widget = self.widgets.get(widget_name)
            if isinstance(widget, QtWidgets.QWidget):
                widget.setEnabled(enabled)

    def _effective_section_line_color(self, entry: ToolboxEntry) -> str:
        custom = (entry.section_line_color or "").strip()
        if custom:
            return custom
        return self.current_section_line_color()

    def _effective_section_title_color(self, entry: ToolboxEntry) -> str:
        custom = (entry.section_title_color or "").strip()
        if custom:
            return custom
        return self.palette().color(QtGui.QPalette.ColorRole.Text).name()

    def _update_section_color_manager_previews(self) -> None:
        selected_line_input = self.widgets[constants.WIDGET_SECTION_SELECTED_LINE_COLOR_INPUT]
        selected_line_preview = self.widgets[constants.WIDGET_SECTION_SELECTED_LINE_COLOR_PREVIEW]
        selected_title_input = self.widgets[constants.WIDGET_SECTION_SELECTED_TITLE_COLOR_INPUT]
        selected_title_preview = self.widgets[constants.WIDGET_SECTION_SELECTED_TITLE_COLOR_PREVIEW]
        all_line_input = self.widgets[constants.WIDGET_SECTION_ALL_LINE_COLOR_INPUT]
        all_line_preview = self.widgets[constants.WIDGET_SECTION_ALL_LINE_COLOR_PREVIEW]
        all_title_input = self.widgets[constants.WIDGET_SECTION_ALL_TITLE_COLOR_INPUT]
        all_title_preview = self.widgets[constants.WIDGET_SECTION_ALL_TITLE_COLOR_PREVIEW]

        selected_target = self._selected_section_entry()
        selected_line_default = (
            self._effective_section_line_color(selected_target[1])
            if selected_target is not None
            else self.current_section_line_color()
        )
        selected_title_default = (
            self._effective_section_title_color(selected_target[1])
            if selected_target is not None
            else self.palette().color(QtGui.QPalette.ColorRole.Text).name()
        )
        all_line_default = self.current_section_line_color()
        all_title_default = self.palette().color(QtGui.QPalette.ColorRole.Text).name()

        selected_line_color = self._normalize_optional_section_color(selected_line_input.text())
        if selected_line_color is None:
            selected_line_color = selected_line_default
        elif selected_line_color == "":
            selected_line_color = selected_line_default

        selected_title_color = self._normalize_optional_section_color(selected_title_input.text())
        if selected_title_color is None:
            selected_title_color = selected_title_default
        elif selected_title_color == "":
            selected_title_color = selected_title_default

        all_line_color = self._normalize_optional_section_color(all_line_input.text())
        if all_line_color is None or all_line_color == "":
            all_line_color = all_line_default

        all_title_color = self._normalize_optional_section_color(all_title_input.text())
        if all_title_color is None or all_title_color == "":
            all_title_color = all_title_default

        selected_line_preview.setStyleSheet(
            f"background: {selected_line_color}; border: 1px solid palette(mid); border-radius: 4px;"
        )
        selected_title_preview.setStyleSheet(
            f"background: {selected_title_color}; border: 1px solid palette(mid); border-radius: 4px;"
        )
        all_line_preview.setStyleSheet(
            f"background: {all_line_color}; border: 1px solid palette(mid); border-radius: 4px;"
        )
        all_title_preview.setStyleSheet(
            f"background: {all_title_color}; border: 1px solid palette(mid); border-radius: 4px;"
        )

    def _refresh_section_color_manager(self, preserve_selection: bool = True) -> None:
        list_widget = self.widgets.get(constants.WIDGET_SECTION_COLOR_LIST)
        if not isinstance(list_widget, QtWidgets.QListWidget):
            return

        selected_payload: tuple[str, str] | None = None
        if preserve_selection:
            current_item = list_widget.currentItem()
            if current_item is not None:
                data = current_item.data(QtCore.Qt.ItemDataRole.UserRole)
                if isinstance(data, tuple) and len(data) == 2:
                    tab_id, entry_id = data
                    if isinstance(tab_id, str) and isinstance(entry_id, str):
                        selected_payload = (tab_id, entry_id)

        list_widget.blockSignals(True)
        list_widget.clear()
        for ctx, entry in self._iter_all_sections():
            item = QtWidgets.QListWidgetItem(f"[{ctx.title}] {entry.title}")
            item.setData(QtCore.Qt.ItemDataRole.UserRole, (ctx.tab_id, entry.entry_id))
            item.setToolTip(
                f"Tab: {ctx.title}\nSection: {entry.title}\n"
                f"Line: {self._display_optional_section_color(entry.section_line_color)}\n"
                f"Title: {self._display_optional_section_color(entry.section_title_color)}"
            )
            list_widget.addItem(item)

        restored_row = -1
        if selected_payload is not None:
            for row in range(list_widget.count()):
                row_item = list_widget.item(row)
                row_data = row_item.data(QtCore.Qt.ItemDataRole.UserRole)
                if row_data == selected_payload:
                    restored_row = row
                    break

        if restored_row >= 0:
            list_widget.setCurrentRow(restored_row)
        elif list_widget.count() > 0:
            list_widget.setCurrentRow(0)
        list_widget.blockSignals(False)

        self._sync_selected_section_color_inputs()

    def _sync_selected_section_color_inputs(self) -> None:
        selected_line_input = self.widgets[constants.WIDGET_SECTION_SELECTED_LINE_COLOR_INPUT]
        selected_title_input = self.widgets[constants.WIDGET_SECTION_SELECTED_TITLE_COLOR_INPUT]
        selected = self._selected_section_entry()
        if selected is None:
            self._set_selected_section_controls_enabled(False)
            selected_line_input.blockSignals(True)
            selected_line_input.setText("(default)")
            selected_line_input.blockSignals(False)
            selected_title_input.blockSignals(True)
            selected_title_input.setText("(default)")
            selected_title_input.blockSignals(False)
            self._update_section_color_manager_previews()
            return

        _ctx, entry = selected
        self._set_selected_section_controls_enabled(True)
        selected_line_input.blockSignals(True)
        selected_line_input.setText(self._display_optional_section_color(entry.section_line_color))
        selected_line_input.blockSignals(False)
        selected_title_input.blockSignals(True)
        selected_title_input.setText(self._display_optional_section_color(entry.section_title_color))
        selected_title_input.blockSignals(False)
        self._update_section_color_manager_previews()

    def _on_section_color_selection_changed(self, _row: int) -> None:
        self._sync_selected_section_color_inputs()

    def _on_selected_section_line_color_changed(self) -> None:
        line_edit = self.widgets[constants.WIDGET_SECTION_SELECTED_LINE_COLOR_INPUT]
        normalized = self._normalize_optional_section_color(line_edit.text())
        if normalized is None:
            line_edit.setText("(default)")
            self.status.showMessage("Invalid color. Use hex like #44aa77 or 'default'.", 2500)
        else:
            line_edit.setText(self._display_optional_section_color(normalized))
        self._update_section_color_manager_previews()

    def _on_selected_section_title_color_changed(self) -> None:
        line_edit = self.widgets[constants.WIDGET_SECTION_SELECTED_TITLE_COLOR_INPUT]
        normalized = self._normalize_optional_section_color(line_edit.text())
        if normalized is None:
            line_edit.setText("(default)")
            self.status.showMessage("Invalid color. Use hex like #ffffff or 'default'.", 2500)
        else:
            line_edit.setText(self._display_optional_section_color(normalized))
        self._update_section_color_manager_previews()

    def _choose_selected_section_line_color(self) -> None:
        selected = self._selected_section_entry()
        if selected is None:
            return
        _ctx, entry = selected
        initial_color = QtGui.QColor(self._effective_section_line_color(entry))
        color = QtWidgets.QColorDialog.getColor(initial_color, self, "Choose Separator Line Color")
        if not color.isValid():
            return
        line_edit = self.widgets[constants.WIDGET_SECTION_SELECTED_LINE_COLOR_INPUT]
        line_edit.setText(color.name())
        self._on_selected_section_line_color_changed()

    def _choose_selected_section_title_color(self) -> None:
        selected = self._selected_section_entry()
        if selected is None:
            return
        _ctx, entry = selected
        initial_color = QtGui.QColor(self._effective_section_title_color(entry))
        color = QtWidgets.QColorDialog.getColor(initial_color, self, "Choose Separator Title Color")
        if not color.isValid():
            return
        line_edit = self.widgets[constants.WIDGET_SECTION_SELECTED_TITLE_COLOR_INPUT]
        line_edit.setText(color.name())
        self._on_selected_section_title_color_changed()

    def _apply_selected_section_line_color(self) -> None:
        selected = self._selected_section_entry()
        if selected is None:
            self.status.showMessage("No separator selected.", 2000)
            return
        ctx, entry = selected
        line_edit = self.widgets[constants.WIDGET_SECTION_SELECTED_LINE_COLOR_INPUT]
        normalized = self._normalize_optional_section_color(line_edit.text())
        if normalized is None:
            self.status.showMessage("Invalid line color.", 2500)
            return
        if entry.section_line_color == normalized:
            self.status.showMessage("Line color already set.", 1500)
            return
        entry.section_line_color = normalized
        self.persist_toolbox_state()
        self.refresh_canvas(ctx)
        self._refresh_section_color_manager()
        self.status.showMessage("Separator line color updated.", 2500)

    def _apply_selected_section_title_color(self) -> None:
        selected = self._selected_section_entry()
        if selected is None:
            self.status.showMessage("No separator selected.", 2000)
            return
        ctx, entry = selected
        line_edit = self.widgets[constants.WIDGET_SECTION_SELECTED_TITLE_COLOR_INPUT]
        normalized = self._normalize_optional_section_color(line_edit.text())
        if normalized is None:
            self.status.showMessage("Invalid title color.", 2500)
            return
        if entry.section_title_color == normalized:
            self.status.showMessage("Title color already set.", 1500)
            return
        entry.section_title_color = normalized
        self.persist_toolbox_state()
        self.refresh_canvas(ctx)
        self._refresh_section_color_manager()
        self.status.showMessage("Separator title color updated.", 2500)

    def _on_all_section_line_color_changed(self) -> None:
        line_edit = self.widgets[constants.WIDGET_SECTION_ALL_LINE_COLOR_INPUT]
        normalized = self._normalize_optional_section_color(line_edit.text())
        if normalized is None:
            line_edit.setText(self.current_section_line_color())
            self.status.showMessage("Invalid color. Use hex like #44aa77 or 'default'.", 2500)
        else:
            line_edit.setText(self._display_optional_section_color(normalized))
        self._update_section_color_manager_previews()

    def _on_all_section_title_color_changed(self) -> None:
        line_edit = self.widgets[constants.WIDGET_SECTION_ALL_TITLE_COLOR_INPUT]
        normalized = self._normalize_optional_section_color(line_edit.text())
        if normalized is None:
            line_edit.setText("(default)")
            self.status.showMessage("Invalid color. Use hex like #ffffff or 'default'.", 2500)
        else:
            line_edit.setText(self._display_optional_section_color(normalized))
        self._update_section_color_manager_previews()

    def _choose_all_section_line_color(self) -> None:
        line_edit = self.widgets[constants.WIDGET_SECTION_ALL_LINE_COLOR_INPUT]
        current = self._normalize_optional_section_color(line_edit.text())
        base_color = self.current_section_line_color() if current in (None, "") else current
        color = QtWidgets.QColorDialog.getColor(
            QtGui.QColor(base_color),
            self,
            "Choose Color for All Separator Lines",
        )
        if not color.isValid():
            return
        line_edit.setText(color.name())
        self._on_all_section_line_color_changed()

    def _choose_all_section_title_color(self) -> None:
        line_edit = self.widgets[constants.WIDGET_SECTION_ALL_TITLE_COLOR_INPUT]
        current = self._normalize_optional_section_color(line_edit.text())
        base_color = (
            self.palette().color(QtGui.QPalette.ColorRole.Text).name()
            if current in (None, "")
            else current
        )
        color = QtWidgets.QColorDialog.getColor(
            QtGui.QColor(base_color),
            self,
            "Choose Color for All Separator Titles",
        )
        if not color.isValid():
            return
        line_edit.setText(color.name())
        self._on_all_section_title_color_changed()

    def _apply_all_section_line_color(self) -> None:
        line_edit = self.widgets[constants.WIDGET_SECTION_ALL_LINE_COLOR_INPUT]
        normalized = self._normalize_optional_section_color(line_edit.text())
        if normalized is None:
            self.status.showMessage("Invalid line color.", 2500)
            return
        changed = False
        for _ctx, entry in self._iter_all_sections():
            if entry.section_line_color == normalized:
                continue
            entry.section_line_color = normalized
            changed = True
        if not changed:
            self.status.showMessage("No line color changes needed.", 2000)
            return
        self.persist_toolbox_state()
        self.refresh_all_canvases(apply_layout_only=True)
        self._refresh_section_color_manager()
        self.status.showMessage("Applied line color to all separators.", 2500)

    def _apply_all_section_title_color(self) -> None:
        line_edit = self.widgets[constants.WIDGET_SECTION_ALL_TITLE_COLOR_INPUT]
        normalized = self._normalize_optional_section_color(line_edit.text())
        if normalized is None:
            self.status.showMessage("Invalid title color.", 2500)
            return
        changed = False
        for _ctx, entry in self._iter_all_sections():
            if entry.section_title_color == normalized:
                continue
            entry.section_title_color = normalized
            changed = True
        if not changed:
            self.status.showMessage("No title color changes needed.", 2000)
            return
        self.persist_toolbox_state()
        self.refresh_all_canvases(apply_layout_only=True)
        self._refresh_section_color_manager()
        self.status.showMessage("Applied title color to all separators.", 2500)

    def _apply_quick_all_section_line_color(self, button_name: str) -> None:
        button = self.widgets.get(button_name)
        if not isinstance(button, QtWidgets.QPushButton):
            return
        quick_color = str(button.property("quick_color") or "")
        line_edit = self.widgets[constants.WIDGET_SECTION_ALL_LINE_COLOR_INPUT]
        line_edit.setText(self._display_optional_section_color(quick_color))
        self._on_all_section_line_color_changed()
        self._apply_all_section_line_color()

    def _apply_quick_all_section_title_color(self, button_name: str) -> None:
        button = self.widgets.get(button_name)
        if not isinstance(button, QtWidgets.QPushButton):
            return
        quick_color = str(button.property("quick_color") or "")
        line_edit = self.widgets[constants.WIDGET_SECTION_ALL_TITLE_COLOR_INPUT]
        line_edit.setText(self._display_optional_section_color(quick_color))
        self._on_all_section_title_color_changed()
        self._apply_all_section_title_color()
