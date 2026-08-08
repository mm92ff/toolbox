#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Load UI settings from QSettings into runtime state/widgets."""

from __future__ import annotations

from collections.abc import Sequence

from PySide6 import QtCore

from app import constants
from app.features.settings.schema import SETTING_SPEC_BY_NAME


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
        constants.WIDGET_TILE_FONT_SIZE_SLIDER,
        settings.value(
            "layout/tile_font_size",
            constants.DEFAULT_TILE_FONT_SIZE,
            type=int,
        ),
    )
    tile_font_auto = owner.widgets[constants.WIDGET_TILE_FONT_AUTO_CHECKBOX]
    tile_font_auto.blockSignals(True)
    tile_font_auto.setChecked(
        settings.value(
            "layout/tile_font_auto",
            constants.DEFAULT_TILE_FONT_AUTO,
            type=bool,
        )
    )
    tile_font_auto.blockSignals(False)
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

    preview_overlay_checkbox = owner.widgets.get(constants.WIDGET_PREVIEW_OVERLAY_CHECKBOX)
    if preview_overlay_checkbox:
        preview_overlay_checkbox.blockSignals(True)
        preview_overlay_checkbox.setChecked(
            settings.value(
                "layout/preview_overlay_enabled",
                constants.DEFAULT_PREVIEW_OVERLAY_ENABLED,
                type=bool,
            )
        )
        preview_overlay_checkbox.blockSignals(False)

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

    show_tray_icon_checkbox = owner.widgets.get(constants.WIDGET_SHOW_TRAY_ICON_CHECKBOX)
    if show_tray_icon_checkbox:
        spec = SETTING_SPEC_BY_NAME["show_tray_icon"]
        show_tray_icon_checkbox.blockSignals(True)
        show_tray_icon_checkbox.setChecked(
            settings.value(spec.qsettings_key, spec.default, type=bool)
        )
        show_tray_icon_checkbox.blockSignals(False)

    minimize_tray_checkbox = owner.widgets.get(
        constants.WIDGET_MINIMIZE_TO_TRAY_CHECKBOX
    )
    if minimize_tray_checkbox:
        spec = SETTING_SPEC_BY_NAME["minimize_to_tray"]
        minimize_tray_checkbox.blockSignals(True)
        minimize_tray_checkbox.setChecked(
            settings.value(spec.qsettings_key, spec.default, type=bool)
        )
        minimize_tray_checkbox.blockSignals(False)
    owner._update_tray_settings_controls_enabled()

    second_launch_combo = owner.widgets.get(
        constants.WIDGET_SECOND_LAUNCH_ACTION_COMBOBOX
    )
    if second_launch_combo is not None:
        spec = SETTING_SPEC_BY_NAME["second_launch_action"]
        action = owner._normalize_second_launch_action(
            settings.value(spec.qsettings_key, spec.default, type=str)
        )
        index = max(0, second_launch_combo.findData(action))
        second_launch_combo.blockSignals(True)
        second_launch_combo.setCurrentIndex(index)
        second_launch_combo.blockSignals(False)

    folder_click_cb = owner.widgets.get(constants.WIDGET_FOLDER_SINGLE_CLICK_CHECKBOX)
    if folder_click_cb:
        spec = SETTING_SPEC_BY_NAME["folder_single_click_browse"]
        folder_click_cb.blockSignals(True)
        folder_click_cb.setChecked(
            settings.value(spec.qsettings_key, spec.default, type=bool)
        )
        folder_click_cb.blockSignals(False)

    folder_file_count_cb = owner.widgets.get(constants.WIDGET_FOLDER_SHOW_FILE_COUNT_CHECKBOX)
    if folder_file_count_cb:
        spec = SETTING_SPEC_BY_NAME["folder_show_file_count"]
        folder_file_count_cb.blockSignals(True)
        folder_file_count_cb.setChecked(
            settings.value(spec.qsettings_key, spec.default, type=bool)
        )
        folder_file_count_cb.blockSignals(False)

    use_system_cb = owner.widgets.get(constants.WIDGET_FILE_ASSOC_USE_SYSTEM_CHECKBOX)
    if use_system_cb:
        spec = SETTING_SPEC_BY_NAME["file_assoc_use_system"]
        use_system_cb.blockSignals(True)
        use_system_cb.setChecked(
            settings.value(spec.qsettings_key, spec.default, type=bool)
        )
        use_system_cb.blockSignals(False)
        # Manually trigger the enable/disable logic
        from PySide6 import QtWidgets as _QtWidgets
        custom_container = use_system_cb.parent().findChild(_QtWidgets.QWidget, "file_assoc_custom_container")
        if custom_container:
            custom_container.setEnabled(not use_system_cb.isChecked())

    for name, widget_key in [
        ("file_assoc_audio", constants.WIDGET_FILE_ASSOC_AUDIO_INPUT),
        ("file_assoc_video", constants.WIDGET_FILE_ASSOC_VIDEO_INPUT),
        ("file_assoc_image", constants.WIDGET_FILE_ASSOC_IMAGE_INPUT),
        ("file_assoc_pdf", constants.WIDGET_FILE_ASSOC_PDF_INPUT),
        ("file_assoc_document", constants.WIDGET_FILE_ASSOC_DOCUMENT_INPUT),
    ]:
        inp = owner.widgets.get(widget_key)
        if inp:
            spec = SETTING_SPEC_BY_NAME[name]
            inp.blockSignals(True)
            inp.setText(settings.value(spec.qsettings_key, spec.default, type=str))
            inp.blockSignals(False)

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

    show_tooltips_checkbox = owner.widgets[constants.WIDGET_SHOW_TOOLTIPS_CHECKBOX]
    show_tooltips_spec = SETTING_SPEC_BY_NAME["show_tooltips"]
    show_tooltips_checkbox.blockSignals(True)
    show_tooltips_checkbox.setChecked(
        settings.value(
            show_tooltips_spec.qsettings_key,
            show_tooltips_spec.default,
            type=bool,
        )
    )
    show_tooltips_checkbox.blockSignals(False)

    ffmpeg_manual_path_input = owner.widgets[constants.WIDGET_FFMPEG_MANUAL_PATH_INPUT]
    ffmpeg_manual_path_input.blockSignals(True)
    ffmpeg_manual_path_input.setText(
        owner._normalize_ffmpeg_manual_path(
            settings.value("layout/ffmpeg_manual_path", "", type=str)
        )
    )
    ffmpeg_manual_path_input.blockSignals(False)

    icon_preview_bg_input = owner.widgets[constants.WIDGET_ICON_PREVIEW_BACKGROUND_COLOR_INPUT]
    icon_preview_bg_input.blockSignals(True)
    icon_preview_bg_input.setText(
        owner._normalize_icon_preview_background_color(
            settings.value(
                "layout/icon_preview_background_color",
                constants.DEFAULT_ICON_PREVIEW_BACKGROUND_COLOR,
                type=str,
            )
        )
    )
    icon_preview_bg_input.blockSignals(False)

    auto_compact_left_checkbox = owner.widgets[constants.WIDGET_AUTO_COMPACT_LEFT_CHECKBOX]
    auto_compact_left_checkbox.blockSignals(True)
    auto_compact_left_checkbox.setChecked(
        settings.value("layout/auto_compact_left", constants.DEFAULT_AUTO_COMPACT_LEFT, type=bool)
    )
    auto_compact_left_checkbox.blockSignals(False)

    responsive_checkbox = owner.widgets[
        constants.WIDGET_RESPONSIVE_TOOLBOX_LAYOUT_CHECKBOX
    ]
    responsive_default_migrated = settings.value(
        constants.RESPONSIVE_LAYOUT_DEFAULT_MIGRATION_KEY,
        False,
        type=bool,
    )
    responsive_enabled = _coerce_responsive_layout(
        settings.value(
            "layout/responsive_toolbox_layout",
            constants.DEFAULT_RESPONSIVE_TOOLBOX_LAYOUT,
        )
    )
    if not responsive_default_migrated:
        # The responsive option was introduced disabled during development. Move
        # existing profiles to the new enabled default exactly once; subsequent
        # explicit user choices remain untouched.
        responsive_enabled = constants.DEFAULT_RESPONSIVE_TOOLBOX_LAYOUT
        settings.setValue("layout/responsive_toolbox_layout", responsive_enabled)
        settings.setValue(constants.RESPONSIVE_LAYOUT_DEFAULT_MIGRATION_KEY, True)
        settings.sync()
    responsive_checkbox.blockSignals(True)
    responsive_checkbox.setChecked(responsive_enabled)
    responsive_checkbox.blockSignals(False)

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
    launch_mode_spec = SETTING_SPEC_BY_NAME["tool_launch_mode"]
    saved_launch_mode = owner._normalize_tool_launch_mode(
        settings.value(
            launch_mode_spec.qsettings_key,
            launch_mode_spec.default,
            type=str,
        )
    )
    launch_mode_index = max(0, launch_mode_combobox.findData(saved_launch_mode))
    launch_mode_combobox.blockSignals(True)
    launch_mode_combobox.setCurrentIndex(launch_mode_index)
    launch_mode_combobox.blockSignals(False)

    owner._update_settings_value_labels()
    owner._update_tile_font_controls_enabled()
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
