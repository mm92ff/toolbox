#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Settings persistence and snapshot I/O helpers for MainWindow."""

from __future__ import annotations

import json
import logging
from collections.abc import Sequence
from pathlib import Path

from PySide6 import QtCore

from app import constants
from app.services.json_io import read_json_utf8, write_json_utf8_atomic

logger = logging.getLogger(__name__)


class MainWindowSettingsIOMixin:
    @staticmethod
    def _normalize_settings_tab_title(value: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized in {"", "einstellungen", "settings"}:
            return "Settings"
        return value.strip()

    @staticmethod
    def _normalize_help_tab_title(value: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized in {"", "hilfe", "help"}:
            return "Help"
        return value.strip()

    def _build_ui_settings_snapshot(self) -> dict[str, object]:
        geometry_base64 = bytes(self.saveGeometry().toBase64()).decode("ascii")
        return {
            "window": {
                "width": self.width(),
                "height": self.height(),
                "geometry_base64": geometry_base64,
            },
            "tabs": {
                "current_index": self.tab_widget.currentIndex(),
                "settings_title": self._settings_title,
                "help_title": self._help_title,
                "hidden_toolbox_tab_ids": sorted(self._hidden_toolbox_tab_ids),
                "help_tab_hidden": self._help_tab_hidden,
            },
            "layout": {
                "icon_size": self.current_icon_size(),
                "tile_frame_enabled": self.current_tile_frame_enabled(),
                "tile_frame_thickness": self.current_tile_frame_thickness(),
                "tile_frame_color": self.current_tile_frame_color(),
                "tile_highlight_color": self.current_tile_highlight_color(),
                "grid_spacing_x": self.current_grid_spacing_x(),
                "grid_spacing_y": self.current_grid_spacing_y(),
                "auto_compact_left": self.current_auto_compact_left(),
                "section_font_size": self.current_section_font_size(),
                "section_line_thickness": self.current_section_line_thickness(),
                "section_gap_above": self.current_section_gap_above(),
                "section_gap_below": self.current_section_gap_below(),
                "section_gap": self.current_section_gap(),
                "section_line_color": self.current_section_line_color(),
            },
            "interaction": {
                "tool_launch_mode": self.current_tool_launch_mode(),
            },
            "toolbox_splitter_sizes": {
                ctx.tab_id: [int(value) for value in ctx.splitter.sizes()]
                for ctx in self.toolbox_tabs
            },
        }

    def _write_json_atomic(self, destination: Path, payload: dict[str, object]) -> None:
        write_json_utf8_atomic(destination, payload, ensure_ascii=False, indent=2)

    def _ui_settings_json_path(self) -> Path:
        return self.config_dir / constants.UI_SETTINGS_FILENAME

    def _read_persisted_ui_settings(self) -> dict[str, object] | None:
        settings_file = self._ui_settings_json_path()
        try:
            payload = read_json_utf8(settings_file)
        except FileNotFoundError:
            return None
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(
                "Could not load persisted UI settings '%s': %s",
                settings_file.name,
                exc,
            )
            return None

        if isinstance(payload, dict):
            schema_version = payload.get("schema_version")
            if schema_version is not None:
                if not isinstance(schema_version, int):
                    logger.warning(
                        "Ignoring UI settings '%s': invalid schema_version type '%s'.",
                        settings_file.name,
                        type(schema_version).__name__,
                    )
                    return None
                if schema_version > 1:
                    logger.warning(
                        "Ignoring UI settings '%s': unsupported schema_version '%s'.",
                        settings_file.name,
                        schema_version,
                    )
                    return None
            raw_ui_settings = payload.get("ui_settings")
            if isinstance(raw_ui_settings, dict):
                return raw_ui_settings
            # Backward compatibility: file may directly contain the snapshot.
            return payload
        return None

    def _persist_ui_settings_json(self) -> None:
        payload = {
            "schema_version": 1,
            "saved_at_utc": QtCore.QDateTime.currentDateTimeUtc().toString(
                QtCore.Qt.DateFormat.ISODate
            ),
            "ui_settings": self._build_ui_settings_snapshot(),
        }
        self._write_json_atomic(self._ui_settings_json_path(), payload)

    def _apply_imported_ui_settings(self, ui_settings: dict[str, object]) -> None:
        settings = QtCore.QSettings()

        window_settings = ui_settings.get("window")
        if isinstance(window_settings, dict):
            settings.setValue(
                "window/width", self._coerce_int(window_settings.get("width"), self.width())
            )
            settings.setValue(
                "window/height", self._coerce_int(window_settings.get("height"), self.height())
            )
            geometry_base64 = window_settings.get("geometry_base64")
            if isinstance(geometry_base64, str) and geometry_base64.strip():
                try:
                    geometry_data = QtCore.QByteArray.fromBase64(geometry_base64.encode("ascii"))
                except UnicodeEncodeError:
                    geometry_data = QtCore.QByteArray()
                if not geometry_data.isEmpty():
                    settings.setValue("geometry", geometry_data)

        tabs_settings = ui_settings.get("tabs")
        if isinstance(tabs_settings, dict):
            settings.setValue(
                "tabs/current_index", self._coerce_int(tabs_settings.get("current_index"), 0)
            )
            settings.setValue(
                "tabs/settings_title",
                self._normalize_settings_tab_title(
                    str(tabs_settings.get("settings_title", "Settings"))
                ),
            )
            settings.setValue(
                "tabs/help_title",
                self._normalize_help_tab_title(str(tabs_settings.get("help_title", "Help"))),
            )
            settings.setValue(
                "tabs/hidden_toolbox_tab_ids",
                self._coerce_str_list(tabs_settings.get("hidden_toolbox_tab_ids", [])),
            )
            settings.setValue(
                "tabs/help_tab_hidden",
                bool(tabs_settings.get("help_tab_hidden", False)),
            )

        layout_settings = ui_settings.get("layout")
        if isinstance(layout_settings, dict):
            settings.setValue(
                "layout/icon_size",
                self._coerce_int(layout_settings.get("icon_size"), constants.DEFAULT_ICON_SIZE),
            )
            settings.setValue(
                "layout/tile_frame_enabled",
                bool(
                    layout_settings.get("tile_frame_enabled", constants.DEFAULT_TILE_FRAME_ENABLED)
                ),
            )
            settings.setValue(
                "layout/tile_frame_thickness",
                self._coerce_int(
                    layout_settings.get("tile_frame_thickness"),
                    constants.DEFAULT_TILE_FRAME_THICKNESS,
                ),
            )
            settings.setValue(
                "layout/tile_frame_color",
                str(layout_settings.get("tile_frame_color", self._default_tile_frame_color())),
            )
            settings.setValue(
                "layout/tile_highlight_color",
                str(
                    layout_settings.get(
                        "tile_highlight_color", self._default_tile_highlight_color()
                    )
                ),
            )
            settings.setValue(
                "layout/grid_spacing_x",
                self._coerce_int(
                    layout_settings.get("grid_spacing_x"), constants.DEFAULT_GRID_SPACING_X
                ),
            )
            settings.setValue(
                "layout/grid_spacing_y",
                self._coerce_int(
                    layout_settings.get("grid_spacing_y"), constants.DEFAULT_GRID_SPACING_Y
                ),
            )
            settings.setValue(
                "layout/auto_compact_left",
                bool(
                    layout_settings.get("auto_compact_left", constants.DEFAULT_AUTO_COMPACT_LEFT)
                ),
            )
            settings.setValue(
                "layout/section_font_size",
                self._coerce_int(
                    layout_settings.get("section_font_size"), constants.DEFAULT_SECTION_FONT_SIZE
                ),
            )
            settings.setValue(
                "layout/section_line_thickness",
                self._coerce_int(
                    layout_settings.get("section_line_thickness"),
                    constants.DEFAULT_SECTION_LINE_THICKNESS,
                ),
            )
            settings.setValue(
                "layout/section_gap_above",
                self._coerce_int(
                    layout_settings.get("section_gap_above"),
                    self._coerce_int(
                        layout_settings.get("section_gap"),
                        constants.DEFAULT_SECTION_PROTECTED_GAP_ABOVE,
                    ),
                ),
            )
            settings.setValue(
                "layout/section_gap_below",
                self._coerce_int(
                    layout_settings.get("section_gap_below"),
                    self._coerce_int(
                        layout_settings.get("section_gap"),
                        constants.DEFAULT_SECTION_PROTECTED_GAP_BELOW,
                    ),
                ),
            )
            settings.setValue(
                "layout/section_gap",
                self._coerce_int(
                    layout_settings.get("section_gap"), constants.DEFAULT_SECTION_PROTECTED_GAP
                ),
            )
            settings.setValue(
                "layout/section_line_color",
                str(
                    layout_settings.get("section_line_color", constants.DEFAULT_SECTION_LINE_COLOR)
                ),
            )

        interaction_settings = ui_settings.get("interaction")
        if isinstance(interaction_settings, dict):
            settings.setValue(
                "interaction/tool_launch_mode",
                self._normalize_tool_launch_mode(
                    str(
                        interaction_settings.get(
                            "tool_launch_mode", constants.DEFAULT_LAUNCH_CLICK_MODE
                        )
                    )
                ),
            )

        splitter_sizes = ui_settings.get("toolbox_splitter_sizes")
        if isinstance(splitter_sizes, dict):
            for tab_id, sizes in splitter_sizes.items():
                if not isinstance(tab_id, str):
                    continue
                if isinstance(sizes, list):
                    normalized_sizes = [self._coerce_int(value, 0) for value in sizes]
                    settings.setValue(f"toolbox/{tab_id}/splitter_sizes", normalized_sizes)

        settings.sync()

    def _load_settings(self) -> None:
        persisted_ui_settings = self._read_persisted_ui_settings()
        if isinstance(persisted_ui_settings, dict):
            # Prefer JSON-backed settings to stay portable across reinstallations.
            self._apply_imported_ui_settings(persisted_ui_settings)

        settings = QtCore.QSettings()
        geometry = settings.value("geometry")
        if isinstance(geometry, QtCore.QByteArray):
            self.restoreGeometry(geometry)
        else:
            self.resize(
                settings.value("window/width", 1100, type=int),
                settings.value("window/height", 760, type=int),
            )

        self._settings_title = self._normalize_settings_tab_title(
            settings.value("tabs/settings_title", "Settings", type=str)
        )
        self._help_title = self._normalize_help_tab_title(
            settings.value("tabs/help_title", "Help", type=str)
        )
        raw_hidden_tab_ids = self._coerce_str_list(
            settings.value("tabs/hidden_toolbox_tab_ids", [])
        )
        known_tab_ids = {ctx.tab_id for ctx in self.toolbox_tabs}
        self._hidden_toolbox_tab_ids = {
            tab_id for tab_id in raw_hidden_tab_ids if tab_id in known_tab_ids
        }
        self._help_tab_hidden = settings.value("tabs/help_tab_hidden", False, type=bool)
        self._reinsert_fixed_tabs()
        self._refresh_tab_manager_ui()

        self._pending_current_tab_index = settings.value("tabs/current_index", 0, type=int)

        self._set_slider_value(
            constants.WIDGET_ICON_SIZE_SLIDER,
            settings.value("layout/icon_size", constants.DEFAULT_ICON_SIZE, type=int),
        )
        self._set_slider_value(
            constants.WIDGET_TILE_FRAME_THICKNESS_SLIDER,
            settings.value(
                "layout/tile_frame_thickness", constants.DEFAULT_TILE_FRAME_THICKNESS, type=int
            ),
        )
        self._set_slider_value(
            constants.WIDGET_GRID_SPACING_X_SLIDER,
            settings.value("layout/grid_spacing_x", constants.DEFAULT_GRID_SPACING_X, type=int),
        )
        self._set_slider_value(
            constants.WIDGET_GRID_SPACING_Y_SLIDER,
            settings.value("layout/grid_spacing_y", constants.DEFAULT_GRID_SPACING_Y, type=int),
        )
        self._set_slider_value(
            constants.WIDGET_SECTION_FONT_SIZE_SLIDER,
            settings.value(
                "layout/section_font_size", constants.DEFAULT_SECTION_FONT_SIZE, type=int
            ),
        )
        self._set_slider_value(
            constants.WIDGET_SECTION_LINE_THICKNESS_SLIDER,
            settings.value(
                "layout/section_line_thickness", constants.DEFAULT_SECTION_LINE_THICKNESS, type=int
            ),
        )

        frame_enabled_checkbox = self.widgets[constants.WIDGET_TILE_FRAME_ENABLED_CHECKBOX]
        frame_enabled_checkbox.blockSignals(True)
        frame_enabled_checkbox.setChecked(
            settings.value(
                "layout/tile_frame_enabled", constants.DEFAULT_TILE_FRAME_ENABLED, type=bool
            )
        )
        frame_enabled_checkbox.blockSignals(False)

        auto_compact_left_checkbox = self.widgets[constants.WIDGET_AUTO_COMPACT_LEFT_CHECKBOX]
        auto_compact_left_checkbox.blockSignals(True)
        auto_compact_left_checkbox.setChecked(
            settings.value(
                "layout/auto_compact_left", constants.DEFAULT_AUTO_COMPACT_LEFT, type=bool
            )
        )
        auto_compact_left_checkbox.blockSignals(False)

        legacy_gap = settings.value(
            "layout/section_gap", constants.DEFAULT_SECTION_PROTECTED_GAP, type=int
        )
        gap_above = settings.value(
            "layout/section_gap_above",
            legacy_gap if legacy_gap is not None else constants.DEFAULT_SECTION_PROTECTED_GAP_ABOVE,
            type=int,
        )
        gap_below = settings.value(
            "layout/section_gap_below",
            legacy_gap if legacy_gap is not None else constants.DEFAULT_SECTION_PROTECTED_GAP_BELOW,
            type=int,
        )

        gap_above_spinbox = self.widgets.get(constants.WIDGET_SECTION_GAP_ABOVE_SPINBOX)
        if gap_above_spinbox is not None:
            gap_above_spinbox.setValue(int(gap_above))
        gap_below_spinbox = self.widgets.get(constants.WIDGET_SECTION_GAP_BELOW_SPINBOX)
        if gap_below_spinbox is not None:
            gap_below_spinbox.setValue(int(gap_below))

        tile_frame_color_input = self.widgets[constants.WIDGET_TILE_FRAME_COLOR_INPUT]
        tile_frame_color_input.setText(
            self._normalize_tile_frame_color(
                settings.value(
                    "layout/tile_frame_color", self._default_tile_frame_color(), type=str
                )
            )
        )

        saved_highlight = settings.value("layout/tile_highlight_color", "", type=str)
        if not saved_highlight:
            saved_highlight = settings.value(
                "layout/tile_fill_color", self._default_tile_highlight_color(), type=str
            )
        tile_highlight_color_input = self.widgets[constants.WIDGET_TILE_HIGHLIGHT_COLOR_INPUT]
        tile_highlight_color_input.setText(self._normalize_tile_highlight_color(saved_highlight))

        color_input = self.widgets[constants.WIDGET_SECTION_LINE_COLOR_INPUT]
        color_input.setText(
            settings.value(
                "layout/section_line_color", constants.DEFAULT_SECTION_LINE_COLOR, type=str
            )
        )

        launch_mode_combobox = self.widgets[constants.WIDGET_TOOL_LAUNCH_MODE_COMBOBOX]
        saved_launch_mode = self._normalize_tool_launch_mode(
            settings.value(
                "interaction/tool_launch_mode", constants.DEFAULT_LAUNCH_CLICK_MODE, type=str
            )
        )
        launch_mode_index = max(0, launch_mode_combobox.findData(saved_launch_mode))
        launch_mode_combobox.blockSignals(True)
        launch_mode_combobox.setCurrentIndex(launch_mode_index)
        launch_mode_combobox.blockSignals(False)

        self._update_settings_value_labels()
        self._update_tile_style_controls_enabled()
        self._update_tile_color_previews()
        self._update_section_color_preview()

        for ctx in self.toolbox_tabs:
            top_sizes = settings.value(f"toolbox/{ctx.tab_id}/splitter_sizes")
            splitter_count = max(1, ctx.splitter.count())
            if (
                isinstance(top_sizes, Sequence)
                and not isinstance(top_sizes, (str, bytes))
                and len(top_sizes) > 0
            ):
                normalized_sizes = [int(value) for value in top_sizes]
                if splitter_count == 1:
                    ctx.splitter.setSizes([normalized_sizes[0]])
                else:
                    if len(normalized_sizes) < splitter_count:
                        normalized_sizes.extend([0] * (splitter_count - len(normalized_sizes)))
                    ctx.splitter.setSizes(normalized_sizes[:splitter_count])
            else:
                if splitter_count == 1:
                    ctx.splitter.setSizes([max(420, self.height() - 60)])
                else:
                    ctx.splitter.setSizes(
                        [
                            constants.TOP_PANEL_DEFAULT_SIZE,
                            max(
                                420,
                                self.height()
                                - constants.TOP_PANEL_DEFAULT_SIZE
                                - constants.BOTTOM_PANEL_DEFAULT_SIZE
                                - 60,
                            ),
                            constants.BOTTOM_PANEL_DEFAULT_SIZE,
                        ][:splitter_count]
                    )

        if 0 <= self._pending_current_tab_index < self.tab_widget.count():
            self.tab_widget.setCurrentIndex(self._pending_current_tab_index)

        self._set_applied_settings(self._capture_pending_settings_from_widgets())
        self._refresh_section_color_manager(preserve_selection=False)
        self._clear_settings_dirty()

    def _save_settings(self) -> None:
        if not getattr(self, "_settings_ready", False):
            return
        settings = QtCore.QSettings()
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("window/width", self.width())
        settings.setValue("window/height", self.height())
        settings.setValue("tabs/current_index", self.tab_widget.currentIndex())
        settings.setValue("tabs/settings_title", self._settings_title)
        settings.setValue("tabs/help_title", self._help_title)
        settings.setValue("tabs/hidden_toolbox_tab_ids", sorted(self._hidden_toolbox_tab_ids))
        settings.setValue("tabs/help_tab_hidden", self._help_tab_hidden)

        settings.setValue("layout/icon_size", self.current_icon_size())
        settings.setValue("layout/tile_frame_enabled", self.current_tile_frame_enabled())
        settings.setValue("layout/tile_frame_thickness", self.current_tile_frame_thickness())
        settings.setValue("layout/tile_frame_color", self.current_tile_frame_color())
        settings.setValue("layout/tile_highlight_color", self.current_tile_highlight_color())
        settings.setValue("layout/grid_spacing_x", self.current_grid_spacing_x())
        settings.setValue("layout/grid_spacing_y", self.current_grid_spacing_y())
        settings.setValue("layout/auto_compact_left", self.current_auto_compact_left())
        settings.setValue("layout/section_font_size", self.current_section_font_size())
        settings.setValue("layout/section_line_thickness", self.current_section_line_thickness())
        settings.setValue("layout/section_gap_above", self.current_section_gap_above())
        settings.setValue("layout/section_gap_below", self.current_section_gap_below())
        settings.setValue("layout/section_gap", self.current_section_gap())
        settings.setValue("layout/section_line_color", self.current_section_line_color())
        settings.setValue("interaction/tool_launch_mode", self.current_tool_launch_mode())

        for ctx in self.toolbox_tabs:
            settings.setValue(f"toolbox/{ctx.tab_id}/splitter_sizes", ctx.splitter.sizes())
        settings.sync()
        try:
            self._persist_ui_settings_json()
        except OSError as exc:
            logger.warning("Could not persist UI settings JSON: %s", exc)

    def _set_slider_value(self, widget_name: str, value: int) -> None:
        slider = self.widgets[widget_name]
        slider.blockSignals(True)
        slider.setValue(value)
        slider.blockSignals(False)
