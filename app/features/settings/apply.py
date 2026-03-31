#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Settings apply-button state and commit behavior."""

from __future__ import annotations

from PySide6 import QtWidgets

from app import constants


class MainWindowSettingsApplyMixin:
    def _mark_settings_dirty(self) -> None:
        self._settings_dirty = True
        self._update_apply_settings_button_state()

    def _clear_settings_dirty(self) -> None:
        self._settings_dirty = False
        self._update_apply_settings_button_state()

    def _update_apply_settings_button_state(self) -> None:
        button = self.widgets.get(constants.BUTTON_APPLY_SETTINGS)
        if isinstance(button, QtWidgets.QPushButton):
            button.setEnabled(bool(getattr(self, "_settings_dirty", False)))

    def _apply_pending_settings(self) -> None:
        if not getattr(self, "_settings_dirty", False):
            self.status.showMessage("No changes to apply.", 2000)
            return

        pending_values = self._capture_pending_settings_from_widgets()
        frame_color_input = self.widgets[constants.WIDGET_TILE_FRAME_COLOR_INPUT]
        highlight_color_input = self.widgets[constants.WIDGET_TILE_HIGHLIGHT_COLOR_INPUT]
        section_color_input = self.widgets[constants.WIDGET_SECTION_LINE_COLOR_INPUT]
        frame_color_input.setText(str(pending_values["tile_frame_color"]))
        highlight_color_input.setText(str(pending_values["tile_highlight_color"]))
        section_color_input.setText(str(pending_values["section_line_color"]))

        tab_settings_changed = self._apply_tab_manager_state_from_ui(
            preferred_key=self._selected_tab_manager_key(), rebuild_ui=True
        )
        self._set_applied_settings(pending_values)
        if tab_settings_changed:
            self.persist_toolbox_state()
        self.refresh_all_canvases(apply_layout_only=True)
        self._save_settings()
        self._clear_settings_dirty()
        self.status.showMessage("Settings saved and applied.", 3000)
