#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Apply imported UI settings payloads into QSettings."""

from __future__ import annotations

from PySide6 import QtCore

from app import constants


def apply_imported_ui_settings(owner: object, ui_settings: dict[str, object]) -> None:
    settings = QtCore.QSettings()

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

    interaction_settings = ui_settings.get("interaction")
    if isinstance(interaction_settings, dict):
        settings.setValue(
            "interaction/tool_launch_mode",
            owner._normalize_tool_launch_mode(
                str(
                    interaction_settings.get(
                        "tool_launch_mode",
                        constants.DEFAULT_LAUNCH_CLICK_MODE,
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
                normalized_sizes = [owner._coerce_int(value, 0) for value in sizes]
                settings.setValue(f"toolbox/{tab_id}/splitter_sizes", normalized_sizes)

    settings.sync()
