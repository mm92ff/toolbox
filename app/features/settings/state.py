#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Settings state, normalization, and applied-value accessors."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6 import QtGui

from app import constants


class MainWindowSettingsStateMixin:
    @staticmethod
    def _coerce_int(value: object, default: int) -> int:
        try:
            return int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _coerce_str_list(value: object) -> list[str]:
        if isinstance(value, str):
            normalized = value.strip()
            return [normalized] if normalized else []
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            result: list[str] = []
            for item in value:
                normalized = str(item).strip()
                if normalized:
                    result.append(normalized)
            return result
        return []

    def _initialize_applied_settings_defaults(self) -> None:
        self._applied_icon_size = constants.DEFAULT_ICON_SIZE
        self._applied_tile_frame_enabled = constants.DEFAULT_TILE_FRAME_ENABLED
        self._applied_image_file_preview_enabled = constants.DEFAULT_IMAGE_FILE_PREVIEW_ENABLED
        self._applied_image_file_preview_mode = constants.DEFAULT_IMAGE_FILE_PREVIEW_MODE
        self._applied_video_file_preview_enabled = constants.DEFAULT_VIDEO_FILE_PREVIEW_ENABLED
        self._applied_hover_preview_enabled = constants.DEFAULT_HOVER_PREVIEW_ENABLED
        self._applied_ffmpeg_manual_path = ""
        self._applied_tile_frame_thickness = constants.DEFAULT_TILE_FRAME_THICKNESS
        self._applied_tile_frame_color = constants.DEFAULT_TILE_FRAME_COLOR
        self._applied_tile_highlight_color = constants.DEFAULT_TILE_HIGHLIGHT_COLOR
        self._applied_grid_spacing_x = constants.DEFAULT_GRID_SPACING_X
        self._applied_grid_spacing_y = constants.DEFAULT_GRID_SPACING_Y
        self._applied_auto_compact_left = constants.DEFAULT_AUTO_COMPACT_LEFT
        self._applied_section_font_size = constants.DEFAULT_SECTION_FONT_SIZE
        self._applied_section_line_thickness = constants.DEFAULT_SECTION_LINE_THICKNESS
        self._applied_section_gap_above = constants.DEFAULT_SECTION_PROTECTED_GAP_ABOVE
        self._applied_section_gap_below = constants.DEFAULT_SECTION_PROTECTED_GAP_BELOW
        self._applied_section_line_color = constants.DEFAULT_SECTION_LINE_COLOR
        self._applied_tool_launch_mode = constants.DEFAULT_LAUNCH_CLICK_MODE

    def _capture_pending_settings_from_widgets(self) -> dict[str, object]:
        icon_slider = self.widgets[constants.WIDGET_ICON_SIZE_SLIDER]
        frame_enabled_checkbox = self.widgets[constants.WIDGET_TILE_FRAME_ENABLED_CHECKBOX]
        image_preview_checkbox = self.widgets[constants.WIDGET_IMAGE_FILE_PREVIEW_CHECKBOX]
        image_preview_mode_combobox = self.widgets[constants.WIDGET_IMAGE_FILE_PREVIEW_MODE_COMBOBOX]
        video_preview_checkbox = self.widgets[constants.WIDGET_VIDEO_FILE_PREVIEW_CHECKBOX]
        hover_preview_checkbox = self.widgets[constants.WIDGET_HOVER_PREVIEW_CHECKBOX]
        ffmpeg_manual_path_input = self.widgets[constants.WIDGET_FFMPEG_MANUAL_PATH_INPUT]
        frame_thickness_slider = self.widgets[constants.WIDGET_TILE_FRAME_THICKNESS_SLIDER]
        frame_color_input = self.widgets[constants.WIDGET_TILE_FRAME_COLOR_INPUT]
        highlight_color_input = self.widgets[constants.WIDGET_TILE_HIGHLIGHT_COLOR_INPUT]
        grid_x_slider = self.widgets[constants.WIDGET_GRID_SPACING_X_SLIDER]
        grid_y_slider = self.widgets[constants.WIDGET_GRID_SPACING_Y_SLIDER]
        auto_compact_checkbox = self.widgets[constants.WIDGET_AUTO_COMPACT_LEFT_CHECKBOX]
        section_font_slider = self.widgets[constants.WIDGET_SECTION_FONT_SIZE_SLIDER]
        section_line_slider = self.widgets[constants.WIDGET_SECTION_LINE_THICKNESS_SLIDER]
        section_gap_above_spinbox = self.widgets.get(constants.WIDGET_SECTION_GAP_ABOVE_SPINBOX)
        section_gap_below_spinbox = self.widgets.get(constants.WIDGET_SECTION_GAP_BELOW_SPINBOX)
        section_gap_spinbox = self.widgets.get(constants.WIDGET_SECTION_GAP_SPINBOX)
        section_color_input = self.widgets[constants.WIDGET_SECTION_LINE_COLOR_INPUT]
        launch_mode_combo = self.widgets[constants.WIDGET_TOOL_LAUNCH_MODE_COMBOBOX]
        fallback_gap = (
            int(section_gap_spinbox.value())
            if section_gap_spinbox is not None
            else constants.DEFAULT_SECTION_PROTECTED_GAP
        )

        return {
            "icon_size": int(icon_slider.value()),
            "tile_frame_enabled": bool(frame_enabled_checkbox.isChecked()),
            "image_file_preview_enabled": bool(image_preview_checkbox.isChecked()),
            "image_file_preview_mode": self._normalize_image_file_preview_mode(
                str(image_preview_mode_combobox.currentData())
            ),
            "video_file_preview_enabled": bool(video_preview_checkbox.isChecked()),
            "hover_preview_enabled": bool(hover_preview_checkbox.isChecked()),
            "ffmpeg_manual_path": self._normalize_ffmpeg_manual_path(
                ffmpeg_manual_path_input.text()
            ),
            "tile_frame_thickness": int(frame_thickness_slider.value()),
            "tile_frame_color": self._normalize_tile_frame_color(frame_color_input.text()),
            "tile_highlight_color": self._normalize_tile_highlight_color(
                highlight_color_input.text()
            ),
            "grid_spacing_x": int(grid_x_slider.value()),
            "grid_spacing_y": int(grid_y_slider.value()),
            "auto_compact_left": bool(auto_compact_checkbox.isChecked()),
            "section_font_size": int(section_font_slider.value()),
            "section_line_thickness": int(section_line_slider.value()),
            "section_gap_above": (
                int(section_gap_above_spinbox.value())
                if section_gap_above_spinbox is not None
                else fallback_gap
            ),
            "section_gap_below": (
                int(section_gap_below_spinbox.value())
                if section_gap_below_spinbox is not None
                else fallback_gap
            ),
            # Keep legacy snapshot key for backward compatibility.
            "section_gap": fallback_gap,
            "section_line_color": self._normalize_section_line_color(section_color_input.text()),
            "tool_launch_mode": self._normalize_tool_launch_mode(
                str(launch_mode_combo.currentData())
            ),
        }

    def _set_applied_settings(self, values: dict[str, object]) -> None:
        self._applied_icon_size = self._coerce_int(
            values.get("icon_size"), constants.DEFAULT_ICON_SIZE
        )
        self._applied_tile_frame_enabled = bool(
            values.get("tile_frame_enabled", constants.DEFAULT_TILE_FRAME_ENABLED)
        )
        self._applied_image_file_preview_enabled = bool(
            values.get(
                "image_file_preview_enabled", constants.DEFAULT_IMAGE_FILE_PREVIEW_ENABLED
            )
        )
        self._applied_image_file_preview_mode = self._normalize_image_file_preview_mode(
            str(
                values.get(
                    "image_file_preview_mode", constants.DEFAULT_IMAGE_FILE_PREVIEW_MODE
                )
            )
        )
        self._applied_video_file_preview_enabled = bool(
            values.get(
                "video_file_preview_enabled", constants.DEFAULT_VIDEO_FILE_PREVIEW_ENABLED
            )
        )
        self._applied_hover_preview_enabled = bool(
            values.get("hover_preview_enabled", constants.DEFAULT_HOVER_PREVIEW_ENABLED)
        )
        self._applied_ffmpeg_manual_path = self._normalize_ffmpeg_manual_path(
            str(values.get("ffmpeg_manual_path", ""))
        )
        self._applied_tile_frame_thickness = self._coerce_int(
            values.get("tile_frame_thickness"),
            constants.DEFAULT_TILE_FRAME_THICKNESS,
        )
        self._applied_tile_frame_color = self._normalize_tile_frame_color(
            str(values.get("tile_frame_color", ""))
        )
        self._applied_tile_highlight_color = self._normalize_tile_highlight_color(
            str(values.get("tile_highlight_color", ""))
        )
        self._applied_grid_spacing_x = self._coerce_int(
            values.get("grid_spacing_x"), constants.DEFAULT_GRID_SPACING_X
        )
        self._applied_grid_spacing_y = self._coerce_int(
            values.get("grid_spacing_y"), constants.DEFAULT_GRID_SPACING_Y
        )
        self._applied_auto_compact_left = bool(
            values.get("auto_compact_left", constants.DEFAULT_AUTO_COMPACT_LEFT)
        )
        self._applied_section_font_size = self._coerce_int(
            values.get("section_font_size"), constants.DEFAULT_SECTION_FONT_SIZE
        )
        self._applied_section_line_thickness = self._coerce_int(
            values.get("section_line_thickness"),
            constants.DEFAULT_SECTION_LINE_THICKNESS,
        )
        legacy_gap = self._coerce_int(
            values.get("section_gap"), constants.DEFAULT_SECTION_PROTECTED_GAP
        )
        self._applied_section_gap_above = self._coerce_int(
            values.get("section_gap_above"),
            legacy_gap,
        )
        self._applied_section_gap_below = self._coerce_int(
            values.get("section_gap_below"),
            legacy_gap,
        )
        self._applied_section_line_color = self._normalize_section_line_color(
            str(values.get("section_line_color", ""))
        )
        self._applied_tool_launch_mode = self._normalize_tool_launch_mode(
            str(values.get("tool_launch_mode", ""))
        )

    def current_icon_size(self) -> int:
        return int(self._applied_icon_size)

    def current_tile_frame_enabled(self) -> bool:
        return bool(self._applied_tile_frame_enabled)

    def current_tile_frame_thickness(self) -> int:
        return int(self._applied_tile_frame_thickness)

    def current_image_file_preview_enabled(self) -> bool:
        return bool(self._applied_image_file_preview_enabled)

    def current_image_file_preview_mode(self) -> str:
        return str(self._applied_image_file_preview_mode)

    def current_video_file_preview_enabled(self) -> bool:
        return bool(self._applied_video_file_preview_enabled)

    def current_hover_preview_enabled(self) -> bool:
        return bool(self._applied_hover_preview_enabled)

    def current_tile_frame_color(self) -> str:
        return str(self._applied_tile_frame_color)

    def current_tile_highlight_color(self) -> str:
        return str(self._applied_tile_highlight_color)

    def current_ffmpeg_manual_path(self) -> str:
        return str(self._applied_ffmpeg_manual_path)

    def current_grid_spacing_x(self) -> int:
        return int(self._applied_grid_spacing_x)

    def current_grid_spacing_y(self) -> int:
        return int(self._applied_grid_spacing_y)

    def current_auto_compact_left(self) -> bool:
        return bool(self._applied_auto_compact_left)

    def current_section_font_size(self) -> int:
        return int(self._applied_section_font_size)

    def current_section_line_thickness(self) -> int:
        return int(self._applied_section_line_thickness)

    def current_section_gap(self) -> int:
        # Legacy single-gap accessor retained for compatibility.
        return int(max(self._applied_section_gap_above, self._applied_section_gap_below))

    def current_section_gap_above(self) -> int:
        return int(self._applied_section_gap_above)

    def current_section_gap_below(self) -> int:
        return int(self._applied_section_gap_below)

    def current_section_line_color(self) -> str:
        return str(self._applied_section_line_color)

    def current_tool_launch_mode(self) -> str:
        return str(self._applied_tool_launch_mode)

    def _normalize_section_line_color(self, value: str) -> str:
        color = QtGui.QColor((value or "").strip())
        return color.name() if color.isValid() else constants.DEFAULT_SECTION_LINE_COLOR

    def _normalize_tile_frame_color(self, value: str) -> str:
        color = QtGui.QColor((value or "").strip())
        return color.name() if color.isValid() else self._default_tile_frame_color()

    def _normalize_tile_highlight_color(self, value: str) -> str:
        color = QtGui.QColor((value or "").strip())
        return color.name() if color.isValid() else self._default_tile_highlight_color()

    def _normalize_tool_launch_mode(self, value: str) -> str:
        mode = (value or "").strip().lower()
        if mode == constants.LAUNCH_CLICK_MODE_SINGLE:
            return constants.LAUNCH_CLICK_MODE_SINGLE
        return constants.LAUNCH_CLICK_MODE_DOUBLE

    def _normalize_image_file_preview_mode(self, value: str) -> str:
        mode = (value or "").strip().lower()
        if mode == constants.IMAGE_PREVIEW_MODE_FILL:
            return constants.IMAGE_PREVIEW_MODE_FILL
        return constants.IMAGE_PREVIEW_MODE_FIT

    @staticmethod
    def _normalize_ffmpeg_manual_path(value: str) -> str:
        return (value or "").strip().strip('"')

    def _default_tile_frame_color(self) -> str:
        return self.palette().color(QtGui.QPalette.ColorRole.Mid).name()

    def _default_tile_highlight_color(self) -> str:
        return self.palette().color(QtGui.QPalette.ColorRole.Highlight).name()
