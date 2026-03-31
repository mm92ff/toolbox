#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tab manager UI behavior for MainWindow."""

from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtWidgets

from app import constants
from app.domain.tab_context import ToolboxTabContext


class MainWindowTabManagerMixin:
    _TAB_KEY_ROLE = int(QtCore.Qt.ItemDataRole.UserRole)
    _TAB_KIND_ROLE = int(QtCore.Qt.ItemDataRole.UserRole) + 1
    _TAB_KIND_TOOLBOX = "toolbox"
    _TAB_KIND_HELP = "help"
    _TAB_KIND_SETTINGS = "settings"

    def _tab_manager_list_widget(self) -> QtWidgets.QListWidget:
        return self.widgets[constants.WIDGET_TAB_MANAGER_LIST]  # type: ignore[return-value]

    def _tab_manager_key_for_toolbox(self, tab_id: str) -> str:
        return f"toolbox:{tab_id}"

    def _tab_manager_toolbox_id_from_key(self, key: str) -> str:
        _, _, tab_id = key.partition(":")
        return tab_id

    def _selected_tab_manager_key(self) -> Optional[str]:
        tab_list = self._tab_manager_list_widget()
        item = tab_list.currentItem()
        if item is None:
            return None
        raw = item.data(self._TAB_KEY_ROLE)
        return str(raw) if raw is not None else None

    def _visible_toolbox_tabs(self) -> list[ToolboxTabContext]:
        return [ctx for ctx in self.toolbox_tabs if ctx.tab_id not in self._hidden_toolbox_tab_ids]

    def _refresh_tab_manager_ui(self, preferred_key: Optional[str] = None) -> None:
        if preferred_key is None:
            preferred_key = self._selected_tab_manager_key()

        tab_list = self._tab_manager_list_widget()
        self._updating_tab_manager = True
        try:
            tab_list.blockSignals(True)
            tab_list.clear()

            for ctx in self.toolbox_tabs:
                item = QtWidgets.QListWidgetItem(ctx.title)
                item.setData(self._TAB_KEY_ROLE, self._tab_manager_key_for_toolbox(ctx.tab_id))
                item.setData(self._TAB_KIND_ROLE, self._TAB_KIND_TOOLBOX)
                item.setFlags(
                    QtCore.Qt.ItemFlag.ItemIsEnabled
                    | QtCore.Qt.ItemFlag.ItemIsSelectable
                    | QtCore.Qt.ItemFlag.ItemIsUserCheckable
                )
                is_visible = ctx.tab_id not in self._hidden_toolbox_tab_ids
                item.setCheckState(
                    QtCore.Qt.CheckState.Checked if is_visible else QtCore.Qt.CheckState.Unchecked
                )
                tab_list.addItem(item)

            help_item = QtWidgets.QListWidgetItem(self._help_title)
            help_item.setData(self._TAB_KEY_ROLE, "fixed:help")
            help_item.setData(self._TAB_KIND_ROLE, self._TAB_KIND_HELP)
            help_item.setFlags(
                QtCore.Qt.ItemFlag.ItemIsEnabled
                | QtCore.Qt.ItemFlag.ItemIsSelectable
                | QtCore.Qt.ItemFlag.ItemIsUserCheckable
            )
            help_visible = not self._help_tab_hidden
            help_item.setCheckState(
                QtCore.Qt.CheckState.Checked if help_visible else QtCore.Qt.CheckState.Unchecked
            )
            tab_list.addItem(help_item)

            settings_item = QtWidgets.QListWidgetItem(self._settings_title)
            settings_item.setData(self._TAB_KEY_ROLE, "fixed:settings")
            settings_item.setData(self._TAB_KIND_ROLE, self._TAB_KIND_SETTINGS)
            settings_item.setFlags(
                QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable
            )
            settings_item.setCheckState(QtCore.Qt.CheckState.Checked)
            tab_list.addItem(settings_item)

            selected_row = -1
            if preferred_key:
                for row in range(tab_list.count()):
                    row_key = str(tab_list.item(row).data(self._TAB_KEY_ROLE) or "")
                    if row_key == preferred_key:
                        selected_row = row
                        break
            if selected_row < 0 and tab_list.count() > 0:
                selected_row = 0
            if selected_row >= 0:
                tab_list.setCurrentRow(selected_row)
        finally:
            tab_list.blockSignals(False)
            self._updating_tab_manager = False
        self._resize_tab_manager_list_to_contents()
        self._update_tab_manager_buttons_enabled()

    def _resize_tab_manager_list_to_contents(self) -> None:
        tab_list = self._tab_manager_list_widget()
        rows = tab_list.count()
        if rows <= 0:
            tab_list.setFixedHeight(42)
            return

        frame = tab_list.frameWidth() * 2
        row_heights = 0
        for row in range(rows):
            row_height = tab_list.sizeHintForRow(row)
            if row_height <= 0:
                row_height = max(22, tab_list.fontMetrics().height() + 8)
            row_heights += row_height
        tab_list.setFixedHeight(frame + row_heights + 2)

    def _update_tab_manager_buttons_enabled(self, *_args: object) -> None:
        move_up_button = self.widgets[constants.BUTTON_TAB_MOVE_UP]
        move_down_button = self.widgets[constants.BUTTON_TAB_MOVE_DOWN]

        tab_list = self._tab_manager_list_widget()
        current_row = tab_list.currentRow()
        if current_row < 0:
            move_up_button.setEnabled(False)
            move_down_button.setEnabled(False)
            return

        toolbox_rows: list[int] = []
        for row in range(tab_list.count()):
            item = tab_list.item(row)
            kind = str(item.data(self._TAB_KIND_ROLE) or "")
            if kind == self._TAB_KIND_TOOLBOX:
                toolbox_rows.append(row)

        if current_row not in toolbox_rows:
            move_up_button.setEnabled(False)
            move_down_button.setEnabled(False)
            return

        position = toolbox_rows.index(current_row)
        move_up_button.setEnabled(position > 0)
        move_down_button.setEnabled(position < len(toolbox_rows) - 1)

    def _apply_tab_manager_state_from_ui(
        self, preferred_key: Optional[str], rebuild_ui: bool = True
    ) -> bool:
        tab_list = self._tab_manager_list_widget()
        ordered_toolbox_ids: list[str] = []
        hidden_toolbox_ids: set[str] = set()
        help_hidden = self._help_tab_hidden

        for row in range(tab_list.count()):
            item = tab_list.item(row)
            kind = str(item.data(self._TAB_KIND_ROLE) or "")
            key = str(item.data(self._TAB_KEY_ROLE) or "")
            checked = item.checkState() == QtCore.Qt.CheckState.Checked
            if kind == self._TAB_KIND_TOOLBOX:
                tab_id = self._tab_manager_toolbox_id_from_key(key)
                if tab_id:
                    ordered_toolbox_ids.append(tab_id)
                    if not checked:
                        hidden_toolbox_ids.add(tab_id)
            elif kind == self._TAB_KIND_HELP:
                help_hidden = not checked

        contexts_by_id = {ctx.tab_id: ctx for ctx in self.toolbox_tabs}
        reordered_tabs: list[ToolboxTabContext] = []
        for tab_id in ordered_toolbox_ids:
            ctx = contexts_by_id.pop(tab_id, None)
            if ctx is not None:
                reordered_tabs.append(ctx)
        reordered_tabs.extend(contexts_by_id.values())
        known_ids = {ctx.tab_id for ctx in reordered_tabs}
        normalized_hidden_ids = {tab_id for tab_id in hidden_toolbox_ids if tab_id in known_ids}
        changed = (
            [ctx.tab_id for ctx in self.toolbox_tabs] != [ctx.tab_id for ctx in reordered_tabs]
            or self._hidden_toolbox_tab_ids != normalized_hidden_ids
            or self._help_tab_hidden != help_hidden
        )
        self.toolbox_tabs = reordered_tabs
        self._hidden_toolbox_tab_ids = normalized_hidden_ids
        self._help_tab_hidden = help_hidden

        if rebuild_ui:
            preferred_widget = self.tab_widget.currentWidget()
            self._reinsert_fixed_tabs(preferred_widget=preferred_widget)
            self._refresh_tab_manager_ui(preferred_key=preferred_key)
        return changed

    def _on_tab_manager_item_changed(self, _item: QtWidgets.QListWidgetItem) -> None:
        if self._updating_tab_manager:
            return
        self._mark_settings_dirty()

    def _move_selected_tab_in_manager(self, delta: int) -> None:
        if delta == 0 or self._updating_tab_manager:
            return

        tab_list = self._tab_manager_list_widget()
        current_row = tab_list.currentRow()
        if current_row < 0:
            return

        current_item = tab_list.item(current_row)
        if current_item is None:
            return
        current_kind = str(current_item.data(self._TAB_KIND_ROLE) or "")
        if current_kind != self._TAB_KIND_TOOLBOX:
            self.status.showMessage("Only toolbox tabs can be moved.", 2500)
            return

        toolbox_rows: list[int] = []
        for row in range(tab_list.count()):
            row_item = tab_list.item(row)
            if row_item is None:
                continue
            row_kind = str(row_item.data(self._TAB_KIND_ROLE) or "")
            if row_kind == self._TAB_KIND_TOOLBOX:
                toolbox_rows.append(row)

        if current_row not in toolbox_rows:
            return
        current_position = toolbox_rows.index(current_row)
        target_position = current_position + delta
        if target_position < 0 or target_position >= len(toolbox_rows):
            return

        target_row = toolbox_rows[target_position]
        moved_item = tab_list.takeItem(current_row)
        if moved_item is None:
            return
        tab_list.insertItem(target_row, moved_item)
        tab_list.setCurrentRow(target_row)
        self._update_tab_manager_buttons_enabled()
        self._mark_settings_dirty()
