#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Appearance settings UI reactions and preview rendering."""

from __future__ import annotations

from PySide6 import QtGui, QtWidgets

from app import constants


class MainWindowSettingsAppearanceMixin:
    def _update_settings_value_labels(self) -> None:
        for slider_name, label_name in (
            (constants.WIDGET_ICON_SIZE_SLIDER, constants.WIDGET_ICON_SIZE_VALUE),
            (
                constants.WIDGET_TILE_FRAME_THICKNESS_SLIDER,
                constants.WIDGET_TILE_FRAME_THICKNESS_VALUE,
            ),
            (constants.WIDGET_GRID_SPACING_X_SLIDER, constants.WIDGET_GRID_SPACING_X_VALUE),
            (constants.WIDGET_GRID_SPACING_Y_SLIDER, constants.WIDGET_GRID_SPACING_Y_VALUE),
            (constants.WIDGET_SECTION_FONT_SIZE_SLIDER, constants.WIDGET_SECTION_FONT_SIZE_VALUE),
            (
                constants.WIDGET_SECTION_LINE_THICKNESS_SLIDER,
                constants.WIDGET_SECTION_LINE_THICKNESS_VALUE,
            ),
        ):
            slider = self.widgets[slider_name]
            label = self.widgets[label_name]
            label.setText(str(slider.value()))

    def _update_section_color_preview(self) -> None:
        preview = self.widgets[constants.WIDGET_SECTION_LINE_COLOR_PREVIEW]
        line_edit = self.widgets[constants.WIDGET_SECTION_LINE_COLOR_INPUT]
        color = self._normalize_section_line_color(line_edit.text())
        preview.setStyleSheet(
            f"background: {color}; border: 1px solid palette(mid); border-radius: 4px;"
        )

    def _update_tile_color_previews(self) -> None:
        frame_preview = self.widgets[constants.WIDGET_TILE_FRAME_COLOR_PREVIEW]
        frame_input = self.widgets[constants.WIDGET_TILE_FRAME_COLOR_INPUT]
        highlight_input = self.widgets[constants.WIDGET_TILE_HIGHLIGHT_COLOR_INPUT]
        frame_color = self._normalize_tile_frame_color(frame_input.text())
        highlight_color = self._normalize_tile_highlight_color(highlight_input.text())
        frame_preview.setStyleSheet(
            f"background: {frame_color}; border: 1px solid palette(mid); border-radius: 4px;"
        )
        highlight_preview = self.widgets[constants.WIDGET_TILE_HIGHLIGHT_COLOR_PREVIEW]
        highlight_preview.setStyleSheet(
            f"background: {highlight_color}; border: 1px solid palette(mid); border-radius: 4px;"
        )

    def _update_tile_style_controls_enabled(self) -> None:
        checkbox = self.widgets[constants.WIDGET_TILE_FRAME_ENABLED_CHECKBOX]
        enabled = checkbox.isChecked()
        for widget_name in (
            constants.WIDGET_TILE_FRAME_THICKNESS_SLIDER,
            constants.WIDGET_TILE_FRAME_COLOR_INPUT,
            constants.WIDGET_TILE_FRAME_COLOR_BUTTON,
        ):
            widget = self.widgets[widget_name]
            widget.setEnabled(enabled)

    def _on_layout_settings_changed(self) -> None:
        self._update_settings_value_labels()
        self._update_tile_style_controls_enabled()
        self._update_tile_color_previews()
        self._update_section_color_preview()
        self._mark_settings_dirty()

    def _on_tool_launch_mode_changed(self, *_args: object) -> None:
        self._mark_settings_dirty()

    def _on_tile_frame_color_changed(self) -> None:
        line_edit = self.widgets[constants.WIDGET_TILE_FRAME_COLOR_INPUT]
        line_edit.setText(self._normalize_tile_frame_color(line_edit.text()))
        self._update_tile_color_previews()
        self._mark_settings_dirty()

    def _on_tile_highlight_color_changed(self) -> None:
        line_edit = self.widgets[constants.WIDGET_TILE_HIGHLIGHT_COLOR_INPUT]
        line_edit.setText(self._normalize_tile_highlight_color(line_edit.text()))
        self._update_tile_color_previews()
        self._mark_settings_dirty()

    def _choose_tile_frame_color(self) -> None:
        line_edit = self.widgets[constants.WIDGET_TILE_FRAME_COLOR_INPUT]
        color = QtWidgets.QColorDialog.getColor(
            QtGui.QColor(self._normalize_tile_frame_color(line_edit.text())),
            self,
            "Choose Frame Color",
        )
        if not color.isValid():
            return
        line_edit.setText(color.name())
        self._on_tile_frame_color_changed()

    def _choose_tile_highlight_color(self) -> None:
        line_edit = self.widgets[constants.WIDGET_TILE_HIGHLIGHT_COLOR_INPUT]
        color = QtWidgets.QColorDialog.getColor(
            QtGui.QColor(self._normalize_tile_highlight_color(line_edit.text())),
            self,
            "Choose Highlight Color",
        )
        if not color.isValid():
            return
        line_edit.setText(color.name())
        self._on_tile_highlight_color_changed()

    def _on_section_line_color_changed(self) -> None:
        line_edit = self.widgets[constants.WIDGET_SECTION_LINE_COLOR_INPUT]
        line_edit.setText(self._normalize_section_line_color(line_edit.text()))
        self._update_section_color_preview()
        self._mark_settings_dirty()

    def _choose_section_line_color(self) -> None:
        line_edit = self.widgets[constants.WIDGET_SECTION_LINE_COLOR_INPUT]
        color = QtWidgets.QColorDialog.getColor(
            QtGui.QColor(self._normalize_section_line_color(line_edit.text())),
            self,
            "Choose Separator Color",
        )
        if not color.isValid():
            return
        line_edit.setText(color.name())
        self._on_section_line_color_changed()
