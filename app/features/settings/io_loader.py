#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Load UI settings from QSettings into runtime state/widgets."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6 import QtCore

from app import constants


def load_settings(owner: object) -> None:
    persisted_ui_settings = owner._read_persisted_ui_settings()
    if isinstance(persisted_ui_settings, dict):
        # Prefer JSON-backed settings to stay portable across reinstallations.
        owner._apply_imported_ui_settings(persisted_ui_settings)

    settings = QtCore.QSettings()
    geometry = settings.value("geometry")
    if isinstance(geometry, QtCore.QByteArray):
        owner.restoreGeometry(geometry)
    else:
        owner.resize(
            settings.value("window/width", 1100, type=int),
            settings.value("window/height", 760, type=int),
        )

    owner._settings_title = owner._normalize_settings_tab_title(
        settings.value("tabs/settings_title", "Settings", type=str)
    )
    owner._help_title = owner._normalize_help_tab_title(
        settings.value("tabs/help_title", "Help", type=str)
    )
    raw_hidden_tab_ids = owner._coerce_str_list(settings.value("tabs/hidden_toolbox_tab_ids", []))
    known_tab_ids = {ctx.tab_id for ctx in owner.toolbox_tabs}
    owner._hidden_toolbox_tab_ids = {tab_id for tab_id in raw_hidden_tab_ids if tab_id in known_tab_ids}
    owner._help_tab_hidden = settings.value("tabs/help_tab_hidden", False, type=bool)
    owner._reinsert_fixed_tabs()
    owner._refresh_tab_manager_ui()

    owner._pending_current_tab_index = settings.value("tabs/current_index", 0, type=int)

    owner._set_slider_value(
        constants.WIDGET_ICON_SIZE_SLIDER,
        settings.value("layout/icon_size", constants.DEFAULT_ICON_SIZE, type=int),
    )
    owner._set_slider_value(
        constants.WIDGET_TILE_FRAME_THICKNESS_SLIDER,
        settings.value("layout/tile_frame_thickness", constants.DEFAULT_TILE_FRAME_THICKNESS, type=int),
    )
    owner._set_slider_value(
        constants.WIDGET_GRID_SPACING_X_SLIDER,
        settings.value("layout/grid_spacing_x", constants.DEFAULT_GRID_SPACING_X, type=int),
    )
    owner._set_slider_value(
        constants.WIDGET_GRID_SPACING_Y_SLIDER,
        settings.value("layout/grid_spacing_y", constants.DEFAULT_GRID_SPACING_Y, type=int),
    )
    owner._set_slider_value(
        constants.WIDGET_SECTION_FONT_SIZE_SLIDER,
        settings.value("layout/section_font_size", constants.DEFAULT_SECTION_FONT_SIZE, type=int),
    )
    owner._set_slider_value(
        constants.WIDGET_SECTION_LINE_THICKNESS_SLIDER,
        settings.value("layout/section_line_thickness", constants.DEFAULT_SECTION_LINE_THICKNESS, type=int),
    )

    frame_enabled_checkbox = owner.widgets[constants.WIDGET_TILE_FRAME_ENABLED_CHECKBOX]
    frame_enabled_checkbox.blockSignals(True)
    frame_enabled_checkbox.setChecked(
        settings.value("layout/tile_frame_enabled", constants.DEFAULT_TILE_FRAME_ENABLED, type=bool)
    )
    frame_enabled_checkbox.blockSignals(False)

    image_preview_checkbox = owner.widgets[constants.WIDGET_IMAGE_FILE_PREVIEW_CHECKBOX]
    image_preview_checkbox.blockSignals(True)
    image_preview_checkbox.setChecked(
        settings.value(
            "layout/image_file_preview_enabled",
            constants.DEFAULT_IMAGE_FILE_PREVIEW_ENABLED,
            type=bool,
        )
    )
    image_preview_checkbox.blockSignals(False)

    image_preview_mode_combobox = owner.widgets[constants.WIDGET_IMAGE_FILE_PREVIEW_MODE_COMBOBOX]
    saved_image_preview_mode = owner._normalize_image_file_preview_mode(
        settings.value(
            "layout/image_file_preview_mode",
            constants.DEFAULT_IMAGE_FILE_PREVIEW_MODE,
            type=str,
        )
    )
    image_preview_mode_index = max(0, image_preview_mode_combobox.findData(saved_image_preview_mode))
    image_preview_mode_combobox.blockSignals(True)
    image_preview_mode_combobox.setCurrentIndex(image_preview_mode_index)
    image_preview_mode_combobox.blockSignals(False)

    video_preview_checkbox = owner.widgets[constants.WIDGET_VIDEO_FILE_PREVIEW_CHECKBOX]
    video_preview_checkbox.blockSignals(True)
    video_preview_checkbox.setChecked(
        settings.value(
            "layout/video_file_preview_enabled",
            constants.DEFAULT_VIDEO_FILE_PREVIEW_ENABLED,
            type=bool,
        )
    )
    video_preview_checkbox.blockSignals(False)

    hover_preview_checkbox = owner.widgets[constants.WIDGET_HOVER_PREVIEW_CHECKBOX]
    hover_preview_checkbox.blockSignals(True)
    hover_preview_checkbox.setChecked(
        settings.value(
            "layout/hover_preview_enabled",
            constants.DEFAULT_HOVER_PREVIEW_ENABLED,
            type=bool,
        )
    )
    hover_preview_checkbox.blockSignals(False)

    ffmpeg_manual_path_input = owner.widgets[constants.WIDGET_FFMPEG_MANUAL_PATH_INPUT]
    ffmpeg_manual_path_input.blockSignals(True)
    ffmpeg_manual_path_input.setText(
        owner._normalize_ffmpeg_manual_path(
            settings.value("layout/ffmpeg_manual_path", "", type=str)
        )
    )
    ffmpeg_manual_path_input.blockSignals(False)

    auto_compact_left_checkbox = owner.widgets[constants.WIDGET_AUTO_COMPACT_LEFT_CHECKBOX]
    auto_compact_left_checkbox.blockSignals(True)
    auto_compact_left_checkbox.setChecked(
        settings.value("layout/auto_compact_left", constants.DEFAULT_AUTO_COMPACT_LEFT, type=bool)
    )
    auto_compact_left_checkbox.blockSignals(False)

    legacy_gap = settings.value("layout/section_gap", constants.DEFAULT_SECTION_PROTECTED_GAP, type=int)
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

    gap_above_spinbox = owner.widgets.get(constants.WIDGET_SECTION_GAP_ABOVE_SPINBOX)
    if gap_above_spinbox is not None:
        gap_above_spinbox.setValue(int(gap_above))
    gap_below_spinbox = owner.widgets.get(constants.WIDGET_SECTION_GAP_BELOW_SPINBOX)
    if gap_below_spinbox is not None:
        gap_below_spinbox.setValue(int(gap_below))

    tile_frame_color_input = owner.widgets[constants.WIDGET_TILE_FRAME_COLOR_INPUT]
    tile_frame_color_input.setText(
        owner._normalize_tile_frame_color(
            settings.value("layout/tile_frame_color", owner._default_tile_frame_color(), type=str)
        )
    )

    saved_highlight = settings.value("layout/tile_highlight_color", "", type=str)
    if not saved_highlight:
        saved_highlight = settings.value("layout/tile_fill_color", owner._default_tile_highlight_color(), type=str)
    tile_highlight_color_input = owner.widgets[constants.WIDGET_TILE_HIGHLIGHT_COLOR_INPUT]
    tile_highlight_color_input.setText(owner._normalize_tile_highlight_color(saved_highlight))

    color_input = owner.widgets[constants.WIDGET_SECTION_LINE_COLOR_INPUT]
    color_input.setText(settings.value("layout/section_line_color", constants.DEFAULT_SECTION_LINE_COLOR, type=str))

    launch_mode_combobox = owner.widgets[constants.WIDGET_TOOL_LAUNCH_MODE_COMBOBOX]
    saved_launch_mode = owner._normalize_tool_launch_mode(
        settings.value("interaction/tool_launch_mode", constants.DEFAULT_LAUNCH_CLICK_MODE, type=str)
    )
    launch_mode_index = max(0, launch_mode_combobox.findData(saved_launch_mode))
    launch_mode_combobox.blockSignals(True)
    launch_mode_combobox.setCurrentIndex(launch_mode_index)
    launch_mode_combobox.blockSignals(False)

    owner._update_settings_value_labels()
    owner._update_tile_style_controls_enabled()
    owner._update_tile_color_previews()
    owner._update_section_color_preview()
    owner._update_ffmpeg_status_preview()

    for ctx in owner.toolbox_tabs:
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
                ctx.splitter.setSizes([max(420, owner.height() - 60)])
            else:
                ctx.splitter.setSizes(
                    [
                        constants.TOP_PANEL_DEFAULT_SIZE,
                        max(
                            420,
                            owner.height()
                            - constants.TOP_PANEL_DEFAULT_SIZE
                            - constants.BOTTOM_PANEL_DEFAULT_SIZE
                            - 60,
                        ),
                        constants.BOTTOM_PANEL_DEFAULT_SIZE,
                    ][:splitter_count]
                )

    if 0 <= owner._pending_current_tab_index < owner.tab_widget.count():
        owner.tab_widget.setCurrentIndex(owner._pending_current_tab_index)

    owner._set_applied_settings(owner._capture_pending_settings_from_widgets())
    owner._refresh_section_color_manager(preserve_selection=False)
    owner._clear_settings_dirty()
