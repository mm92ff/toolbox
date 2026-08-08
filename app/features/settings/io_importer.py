#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply imported UI settings payloads into QSettings."""

from __future__ import annotations

from PySide6 import QtCore

from app import constants
from app.features.settings.schema import import_schema_settings


def _coerce_responsive_layout(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().casefold()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return constants.DEFAULT_RESPONSIVE_TOOLBOX_LAYOUT


def apply_imported_ui_settings(owner: object, ui_settings: dict[str, object]) -> None:
    settings = QtCore.QSettings()

    folder_browse_settings = ui_settings.get("folder_browse")
    folder_appearance_store = getattr(owner, "_folder_browse_appearance_store", None)
    load_folder_snapshot = getattr(folder_appearance_store, "load_snapshot", None)
    if isinstance(folder_browse_settings, dict) and callable(load_folder_snapshot):
        load_folder_snapshot(folder_browse_settings)

    window_settings = ui_settings.get("window")
    if isinstance(window_settings, dict):
        settings.setValue(
            "window/width", owner._coerce_int(window_settings.get("width"), owner.width())
        )
        settings.setValue(
            "window/height", owner._coerce_int(window_settings.get("height"), owner.height())
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
        settings.setValue("tabs/current_index", owner._coerce_int(tabs_settings.get("current_index"), 0))
        settings.setValue(
            "tabs/settings_title",
            owner._normalize_settings_tab_title(str(tabs_settings.get("settings_title", "Settings"))),
        )
        settings.setValue(
            "tabs/help_title",
            owner._normalize_help_tab_title(str(tabs_settings.get("help_title", "Help"))),
        )
        settings.setValue(
            "tabs/hidden_toolbox_tab_ids",
            owner._coerce_str_list(tabs_settings.get("hidden_toolbox_tab_ids", [])),
        )
        settings.setValue("tabs/help_tab_hidden", bool(tabs_settings.get("help_tab_hidden", False)))

    layout_settings = ui_settings.get("layout")
    if isinstance(layout_settings, dict):
        settings.setValue(
            "layout/icon_size",
            owner._coerce_int(layout_settings.get("icon_size"), constants.DEFAULT_ICON_SIZE),
        )
        settings.setValue(
            "layout/tile_font_auto",
            bool(
                layout_settings.get(
                    "tile_font_auto",
                    constants.DEFAULT_TILE_FONT_AUTO,
                )
            ),
        )
        settings.setValue(
            "layout/tile_font_size",
            owner._coerce_int(
                layout_settings.get("tile_font_size"),
                constants.DEFAULT_TILE_FONT_SIZE,
            ),
        )
        settings.setValue(
            "layout/tile_frame_enabled",
            bool(layout_settings.get("tile_frame_enabled", constants.DEFAULT_TILE_FRAME_ENABLED)),
        )
        settings.setValue(
            "layout/image_file_preview_enabled",
            bool(
                layout_settings.get(
                    "image_file_preview_enabled",
                    constants.DEFAULT_IMAGE_FILE_PREVIEW_ENABLED,
                )
            ),
        )
        settings.setValue(
            "layout/image_file_preview_mode",
            owner._normalize_image_file_preview_mode(
                str(
                    layout_settings.get(
                        "image_file_preview_mode",
                        constants.DEFAULT_IMAGE_FILE_PREVIEW_MODE,
                    )
                )
            ),
        )
        settings.setValue(
            "layout/preview_overlay_enabled",
            bool(
                layout_settings.get(
                    "preview_overlay_enabled",
                    constants.DEFAULT_PREVIEW_OVERLAY_ENABLED,
                )
            ),
        )
        settings.setValue(
            "layout/video_file_preview_enabled",
            bool(
                layout_settings.get(
                    "video_file_preview_enabled",
                    constants.DEFAULT_VIDEO_FILE_PREVIEW_ENABLED,
                )
            ),
        )
        settings.setValue(
            "layout/hover_preview_enabled",
            bool(
                layout_settings.get(
                    "hover_preview_enabled",
                    constants.DEFAULT_HOVER_PREVIEW_ENABLED,
                )
            ),
        )
        settings.setValue(
            "layout/ffmpeg_manual_path",
            owner._normalize_ffmpeg_manual_path(
                str(layout_settings.get("ffmpeg_manual_path", ""))
            ),
        )
        settings.setValue(
            "layout/icon_preview_background_color",
            owner._normalize_icon_preview_background_color(
                str(
                    layout_settings.get(
                        "icon_preview_background_color",
                        constants.DEFAULT_ICON_PREVIEW_BACKGROUND_COLOR,
                    )
                )
            ),
        )
        settings.setValue(
            "layout/tile_frame_thickness",
            owner._coerce_int(
                layout_settings.get("tile_frame_thickness"),
                constants.DEFAULT_TILE_FRAME_THICKNESS,
            ),
        )
        settings.setValue(
            "layout/tile_frame_color",
            str(layout_settings.get("tile_frame_color", owner._default_tile_frame_color())),
        )
        settings.setValue(
            "layout/tile_highlight_color",
            str(
                layout_settings.get(
                    "tile_highlight_color",
                    owner._default_tile_highlight_color(),
                )
            ),
        )
        settings.setValue(
            "layout/grid_spacing_x",
            owner._coerce_int(layout_settings.get("grid_spacing_x"), constants.DEFAULT_GRID_SPACING_X),
        )
        settings.setValue(
            "layout/grid_spacing_y",
            owner._coerce_int(layout_settings.get("grid_spacing_y"), constants.DEFAULT_GRID_SPACING_Y),
        )
        settings.setValue(
            "layout/auto_compact_left",
            bool(layout_settings.get("auto_compact_left", constants.DEFAULT_AUTO_COMPACT_LEFT)),
        )
        settings.setValue(
            "layout/responsive_toolbox_layout",
            _coerce_responsive_layout(
                layout_settings.get(
                    "responsive_toolbox_layout",
                    constants.DEFAULT_RESPONSIVE_TOOLBOX_LAYOUT,
                )
            ),
        )
        settings.setValue(
            "layout/section_font_size",
            owner._coerce_int(
                layout_settings.get("section_font_size"),
                constants.DEFAULT_SECTION_FONT_SIZE,
            ),
        )
        settings.setValue(
            "layout/section_line_thickness",
            owner._coerce_int(
                layout_settings.get("section_line_thickness"),
                constants.DEFAULT_SECTION_LINE_THICKNESS,
            ),
        )
        settings.setValue(
            "layout/section_gap_above",
            owner._coerce_int(
                layout_settings.get("section_gap_above"),
                owner._coerce_int(
                    layout_settings.get("section_gap"),
                    constants.DEFAULT_SECTION_PROTECTED_GAP_ABOVE,
                ),
            ),
        )
        settings.setValue(
            "layout/section_gap_below",
            owner._coerce_int(
                layout_settings.get("section_gap_below"),
                owner._coerce_int(
                    layout_settings.get("section_gap"),
                    constants.DEFAULT_SECTION_PROTECTED_GAP_BELOW,
                ),
            ),
        )
        settings.setValue(
            "layout/section_gap",
            owner._coerce_int(
                layout_settings.get("section_gap"),
                constants.DEFAULT_SECTION_PROTECTED_GAP,
            ),
        )
        settings.setValue(
            "layout/section_line_color",
            str(layout_settings.get("section_line_color", constants.DEFAULT_SECTION_LINE_COLOR)),
        )

    import_schema_settings(settings, owner, ui_settings)

    splitter_sizes = ui_settings.get("toolbox_splitter_sizes")
    if isinstance(splitter_sizes, dict):
        for tab_id, sizes in splitter_sizes.items():
            if not isinstance(tab_id, str):
                continue
            if isinstance(sizes, list):
                normalized_sizes = [owner._coerce_int(value, 0) for value in sizes]
                settings.setValue(f"toolbox/{tab_id}/splitter_sizes", normalized_sizes)

    settings.sync()
