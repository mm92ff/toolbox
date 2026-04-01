#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Appearance settings UI reactions and preview rendering."""

from __future__ import annotations

from PySide6 import QtGui, QtWidgets

from app import constants
from app.services.video_thumbnails import (
    FFMPEG_SOURCE_ENV,
    FFMPEG_SOURCE_INTERNAL,
    FFMPEG_SOURCE_MANUAL,
    FFMPEG_SOURCE_NOT_FOUND,
    FFMPEG_SOURCE_SYSTEM,
    clear_ffmpeg_resolution_cache,
    resolve_ffmpeg_path,
)


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

    @staticmethod
    def _ffmpeg_source_text(source: str) -> str:
        normalized = (source or "").strip().lower()
        if normalized == FFMPEG_SOURCE_ENV:
            return "Environment override (TOOLBOX_FFMPEG_PATH)"
        if normalized == FFMPEG_SOURCE_MANUAL:
            return "Manual path (Settings)"
        if normalized == FFMPEG_SOURCE_SYSTEM:
            return "System installation (PATH/common locations)"
        if normalized == FFMPEG_SOURCE_INTERNAL:
            return "Bundled internal ffmpeg"
        if normalized == FFMPEG_SOURCE_NOT_FOUND:
            return "Not found"
        return "Unknown"

    def _update_ffmpeg_status_preview(self) -> None:
        source_value = self.widgets.get(constants.WIDGET_FFMPEG_SOURCE_VALUE)
        resolved_path_value = self.widgets.get(constants.WIDGET_FFMPEG_RESOLVED_PATH_VALUE)
        manual_input = self.widgets.get(constants.WIDGET_FFMPEG_MANUAL_PATH_INPUT)
        if source_value is None or resolved_path_value is None or manual_input is None:
            return

        manual_path = self._normalize_ffmpeg_manual_path(manual_input.text())
        resolution = resolve_ffmpeg_path(manual_path or None)
        source_value.setText(self._ffmpeg_source_text(resolution.source))
        resolved_path_value.setText(resolution.path or "(not found)")

    def _on_ffmpeg_manual_path_changed(self) -> None:
        manual_input = self.widgets[constants.WIDGET_FFMPEG_MANUAL_PATH_INPUT]
        manual_input.setText(self._normalize_ffmpeg_manual_path(manual_input.text()))
        clear_ffmpeg_resolution_cache()
        self._update_ffmpeg_status_preview()
        self._mark_settings_dirty()

    def _choose_ffmpeg_manual_path(self) -> None:
        manual_input = self.widgets[constants.WIDGET_FFMPEG_MANUAL_PATH_INPUT]
        selected_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select ffmpeg executable",
            manual_input.text().strip(),
            "Executable (ffmpeg.exe);;All files (*)",
        )
        if not selected_path:
            return
        manual_input.setText(selected_path)
        self._on_ffmpeg_manual_path_changed()

    def _rescan_ffmpeg_status(self) -> None:
        clear_ffmpeg_resolution_cache()
        self._update_ffmpeg_status_preview()
        self.status.showMessage("FFmpeg detection refreshed.", 2000)

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
