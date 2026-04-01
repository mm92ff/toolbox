#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Appearance settings UI reactions and preview rendering."""

from __future__ import annotations

from PySide6 import QtGui, QtWidgets

from app import constants


class MainWindowSettingsAppearanceMixin:
    def _normalize_icon_preview_background_color(self, value: str) -> str:
        color = QtGui.QColor((value or "").strip())
        if not color.isValid():
            return constants.DEFAULT_ICON_PREVIEW_BACKGROUND_COLOR
        return color.name()

    def _update_icon_preview_background_color_preview(self) -> None:
        preview = self.widgets.get(constants.WIDGET_ICON_PREVIEW_BACKGROUND_COLOR_PREVIEW)
        line_edit = self.widgets.get(constants.WIDGET_ICON_PREVIEW_BACKGROUND_COLOR_INPUT)
        if preview is None or line_edit is None:
            return
        color = self._normalize_icon_preview_background_color(line_edit.text())
        preview.setStyleSheet(
            f"background: {color}; border: 1px solid palette(mid); border-radius: 4px;"
        )

    def _update_icon_size_live_preview(self) -> None:
        preview = self.widgets.get(constants.WIDGET_ICON_SIZE_LIVE_PREVIEW)
        if preview is None or not hasattr(preview, "update_preview"):
            return
        icon_slider = self.widgets[constants.WIDGET_ICON_SIZE_SLIDER]
        frame_enabled_checkbox = self.widgets[constants.WIDGET_TILE_FRAME_ENABLED_CHECKBOX]
        frame_thickness_slider = self.widgets[constants.WIDGET_TILE_FRAME_THICKNESS_SLIDER]
        frame_color_input = self.widgets[constants.WIDGET_TILE_FRAME_COLOR_INPUT]
        highlight_color_input = self.widgets[constants.WIDGET_TILE_HIGHLIGHT_COLOR_INPUT]
        grid_x_slider = self.widgets[constants.WIDGET_GRID_SPACING_X_SLIDER]
        grid_y_slider = self.widgets[constants.WIDGET_GRID_SPACING_Y_SLIDER]
        preview_bg_input = self.widgets.get(constants.WIDGET_ICON_PREVIEW_BACKGROUND_COLOR_INPUT)
        preview_bg_color = (
            self._normalize_icon_preview_background_color(preview_bg_input.text())
            if preview_bg_input is not None
            else constants.DEFAULT_ICON_PREVIEW_BACKGROUND_COLOR
        )
        preview.update_preview(
            icon_size=int(icon_slider.value()),
            frame_enabled=bool(frame_enabled_checkbox.isChecked()),
            frame_thickness=int(frame_thickness_slider.value()),
            frame_color=self._normalize_tile_frame_color(frame_color_input.text()),
            highlight_color=self._normalize_tile_highlight_color(highlight_color_input.text()),
            grid_spacing_x=int(grid_x_slider.value()),
            grid_spacing_y=int(grid_y_slider.value()),
            preview_background_color=preview_bg_color,
        )

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
        self._update_icon_size_live_preview()

    def _update_section_color_preview(self) -> None:
        preview = self.widgets[constants.WIDGET_SECTION_LINE_COLOR_PREVIEW]
        line_edit = self.widgets[constants.WIDGET_SECTION_LINE_COLOR_INPUT]
        color = self._normalize_section_line_color(line_edit.text())
        preview.setStyleSheet(
            f"background: {color}; border: 1px solid palette(mid); border-radius: 4px;"
        )
        self._update_section_separator_live_preview()

    def _update_section_separator_live_preview(self) -> None:
        preview = self.widgets.get(constants.WIDGET_SECTION_SEPARATOR_LIVE_PREVIEW)
        if preview is None or not hasattr(preview, "update_preview"):
            return
        font_slider = self.widgets[constants.WIDGET_SECTION_FONT_SIZE_SLIDER]
        line_slider = self.widgets[constants.WIDGET_SECTION_LINE_THICKNESS_SLIDER]
        line_edit = self.widgets[constants.WIDGET_SECTION_LINE_COLOR_INPUT]
        gap_above_spinbox = self.widgets.get(constants.WIDGET_SECTION_GAP_ABOVE_SPINBOX)
        gap_below_spinbox = self.widgets.get(constants.WIDGET_SECTION_GAP_BELOW_SPINBOX)
        gap_above = (
            int(gap_above_spinbox.value())
            if gap_above_spinbox is not None
            else constants.DEFAULT_SECTION_PROTECTED_GAP_ABOVE
        )
        gap_below = (
            int(gap_below_spinbox.value())
            if gap_below_spinbox is not None
            else constants.DEFAULT_SECTION_PROTECTED_GAP_BELOW
        )
        preview.update_preview(
            font_size=int(font_slider.value()),
            line_thickness=int(line_slider.value()),
            line_color=self._normalize_section_line_color(line_edit.text()),
            gap_above=gap_above,
            gap_below=gap_below,
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
        self._update_icon_preview_background_color_preview()

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
        image_preview_checkbox = self.widgets[constants.WIDGET_IMAGE_FILE_PREVIEW_CHECKBOX]
        image_preview_mode = self.widgets[constants.WIDGET_IMAGE_FILE_PREVIEW_MODE_COMBOBOX]
        image_preview_mode.setEnabled(bool(image_preview_checkbox.isChecked()))

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
        self._update_icon_size_live_preview()
        self._mark_settings_dirty()

    def _on_tile_highlight_color_changed(self) -> None:
        line_edit = self.widgets[constants.WIDGET_TILE_HIGHLIGHT_COLOR_INPUT]
        line_edit.setText(self._normalize_tile_highlight_color(line_edit.text()))
        self._update_tile_color_previews()
        self._update_icon_size_live_preview()
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

    def _on_icon_preview_background_color_changed(self) -> None:
        line_edit = self.widgets[constants.WIDGET_ICON_PREVIEW_BACKGROUND_COLOR_INPUT]
        line_edit.setText(self._normalize_icon_preview_background_color(line_edit.text()))
        self._update_icon_preview_background_color_preview()
        self._update_icon_size_live_preview()

    def _choose_icon_preview_background_color(self) -> None:
        line_edit = self.widgets[constants.WIDGET_ICON_PREVIEW_BACKGROUND_COLOR_INPUT]
        color = QtWidgets.QColorDialog.getColor(
            QtGui.QColor(self._normalize_icon_preview_background_color(line_edit.text())),
            self,
            "Choose Preview Background Color",
        )
        if not color.isValid():
            return
        line_edit.setText(color.name())
        self._on_icon_preview_background_color_changed()

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
