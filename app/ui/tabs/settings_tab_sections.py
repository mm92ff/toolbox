#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Section builders used by the Settings tab UI."""

from __future__ import annotations

from typing import Dict

from PySide6 import QtCore, QtWidgets

from app import constants
from app.ui.widgets.icon_size_preview import IconSizeLivePreview
from app.ui.widgets.input_controls import NoWheelComboBox, NoWheelSlider, NoWheelSpinBox
from app.ui.widgets.section_separator_preview import SectionSeparatorLivePreview


def build_appearance_group(widgets: Dict[str, QtWidgets.QWidget]) -> QtWidgets.QGroupBox:
    appearance_group = QtWidgets.QGroupBox("Appearance")
    appearance_layout = QtWidgets.QGridLayout(appearance_group)
    appearance_layout.setColumnStretch(1, 1)

    appearance_layout.addWidget(QtWidgets.QLabel("Icon Size:"), 0, 0)
    icon_slider = NoWheelSlider(QtCore.Qt.Orientation.Horizontal)
    icon_slider.setObjectName(constants.WIDGET_ICON_SIZE_SLIDER)
    icon_slider.setRange(constants.MIN_ICON_SIZE, constants.MAX_ICON_SIZE)
    icon_slider.setSingleStep(4)
    icon_slider.setPageStep(8)
    widgets[constants.WIDGET_ICON_SIZE_SLIDER] = icon_slider
    appearance_layout.addWidget(icon_slider, 0, 1)

    icon_value = QtWidgets.QLabel(str(constants.DEFAULT_ICON_SIZE))
    icon_value.setObjectName(constants.WIDGET_ICON_SIZE_VALUE)
    icon_value.setMinimumWidth(40)
    widgets[constants.WIDGET_ICON_SIZE_VALUE] = icon_value
    appearance_layout.addWidget(icon_value, 0, 2)

    appearance_layout.addWidget(QtWidgets.QLabel("Launch Trigger:"), 1, 0)
    launch_mode_combobox = NoWheelComboBox()
    launch_mode_combobox.setObjectName(constants.WIDGET_TOOL_LAUNCH_MODE_COMBOBOX)
    launch_mode_combobox.addItem("Double-click", constants.LAUNCH_CLICK_MODE_DOUBLE)
    launch_mode_combobox.addItem("Single-click", constants.LAUNCH_CLICK_MODE_SINGLE)
    widgets[constants.WIDGET_TOOL_LAUNCH_MODE_COMBOBOX] = launch_mode_combobox
    appearance_layout.addWidget(launch_mode_combobox, 1, 1, 1, 2)

    appearance_layout.addWidget(QtWidgets.QLabel("Icon Frame:"), 2, 0)
    tile_frame_enabled = QtWidgets.QCheckBox("Show frame")
    tile_frame_enabled.setObjectName(constants.WIDGET_TILE_FRAME_ENABLED_CHECKBOX)
    tile_frame_enabled.setChecked(constants.DEFAULT_TILE_FRAME_ENABLED)
    widgets[constants.WIDGET_TILE_FRAME_ENABLED_CHECKBOX] = tile_frame_enabled
    appearance_layout.addWidget(tile_frame_enabled, 2, 1, 1, 2)

    appearance_layout.addWidget(QtWidgets.QLabel("Image Files:"), 3, 0)
    image_preview_enabled = QtWidgets.QCheckBox("Use image preview thumbnails")
    image_preview_enabled.setObjectName(constants.WIDGET_IMAGE_FILE_PREVIEW_CHECKBOX)
    image_preview_enabled.setChecked(constants.DEFAULT_IMAGE_FILE_PREVIEW_ENABLED)
    widgets[constants.WIDGET_IMAGE_FILE_PREVIEW_CHECKBOX] = image_preview_enabled
    appearance_layout.addWidget(image_preview_enabled, 3, 1, 1, 2)

    appearance_layout.addWidget(QtWidgets.QLabel("Preview Mode:"), 4, 0)
    image_preview_mode = NoWheelComboBox()
    image_preview_mode.setObjectName(constants.WIDGET_IMAGE_FILE_PREVIEW_MODE_COMBOBOX)
    image_preview_mode.addItem("Fit (show full image)", constants.IMAGE_PREVIEW_MODE_FIT)
    image_preview_mode.addItem("Fill and crop", constants.IMAGE_PREVIEW_MODE_FILL)
    widgets[constants.WIDGET_IMAGE_FILE_PREVIEW_MODE_COMBOBOX] = image_preview_mode
    appearance_layout.addWidget(image_preview_mode, 4, 1, 1, 2)

    appearance_layout.addWidget(QtWidgets.QLabel("Video Files:"), 5, 0)
    video_preview_enabled = QtWidgets.QCheckBox("Use video preview thumbnails (ffmpeg)")
    video_preview_enabled.setObjectName(constants.WIDGET_VIDEO_FILE_PREVIEW_CHECKBOX)
    video_preview_enabled.setChecked(constants.DEFAULT_VIDEO_FILE_PREVIEW_ENABLED)
    widgets[constants.WIDGET_VIDEO_FILE_PREVIEW_CHECKBOX] = video_preview_enabled
    appearance_layout.addWidget(video_preview_enabled, 5, 1, 1, 2)

    appearance_layout.addWidget(QtWidgets.QLabel("Hover Preview:"), 6, 0)
    hover_preview_enabled = QtWidgets.QCheckBox("Enlarge image/video preview on mouse hover")
    hover_preview_enabled.setObjectName(constants.WIDGET_HOVER_PREVIEW_CHECKBOX)
    hover_preview_enabled.setChecked(constants.DEFAULT_HOVER_PREVIEW_ENABLED)
    widgets[constants.WIDGET_HOVER_PREVIEW_CHECKBOX] = hover_preview_enabled
    appearance_layout.addWidget(hover_preview_enabled, 6, 1, 1, 2)

    appearance_layout.addWidget(QtWidgets.QLabel("Frame Thickness:"), 7, 0)
    tile_frame_thickness_slider = NoWheelSlider(QtCore.Qt.Orientation.Horizontal)
    tile_frame_thickness_slider.setObjectName(constants.WIDGET_TILE_FRAME_THICKNESS_SLIDER)
    tile_frame_thickness_slider.setRange(
        constants.MIN_TILE_FRAME_THICKNESS, constants.MAX_TILE_FRAME_THICKNESS
    )
    tile_frame_thickness_slider.setSingleStep(1)
    tile_frame_thickness_slider.setPageStep(1)
    widgets[constants.WIDGET_TILE_FRAME_THICKNESS_SLIDER] = tile_frame_thickness_slider
    appearance_layout.addWidget(tile_frame_thickness_slider, 7, 1)

    tile_frame_thickness_value = QtWidgets.QLabel(str(constants.DEFAULT_TILE_FRAME_THICKNESS))
    tile_frame_thickness_value.setObjectName(constants.WIDGET_TILE_FRAME_THICKNESS_VALUE)
    tile_frame_thickness_value.setMinimumWidth(40)
    widgets[constants.WIDGET_TILE_FRAME_THICKNESS_VALUE] = tile_frame_thickness_value
    appearance_layout.addWidget(tile_frame_thickness_value, 7, 2)

    appearance_layout.addWidget(QtWidgets.QLabel("Frame Color:"), 8, 0)
    frame_color_row = QtWidgets.QHBoxLayout()
    tile_frame_color_input = QtWidgets.QLineEdit(constants.DEFAULT_TILE_FRAME_COLOR)
    tile_frame_color_input.setObjectName(constants.WIDGET_TILE_FRAME_COLOR_INPUT)
    widgets[constants.WIDGET_TILE_FRAME_COLOR_INPUT] = tile_frame_color_input
    frame_color_row.addWidget(tile_frame_color_input, 1)

    tile_frame_color_preview = QtWidgets.QLabel()
    tile_frame_color_preview.setObjectName(constants.WIDGET_TILE_FRAME_COLOR_PREVIEW)
    tile_frame_color_preview.setFixedSize(28, 18)
    tile_frame_color_preview.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
    widgets[constants.WIDGET_TILE_FRAME_COLOR_PREVIEW] = tile_frame_color_preview
    frame_color_row.addWidget(tile_frame_color_preview)

    tile_frame_color_button = QtWidgets.QPushButton("Choose Color")
    tile_frame_color_button.setObjectName(constants.WIDGET_TILE_FRAME_COLOR_BUTTON)
    widgets[constants.WIDGET_TILE_FRAME_COLOR_BUTTON] = tile_frame_color_button
    frame_color_row.addWidget(tile_frame_color_button)
    appearance_layout.addLayout(frame_color_row, 8, 1, 1, 2)

    appearance_layout.addWidget(QtWidgets.QLabel("Highlight Color:"), 9, 0)
    highlight_color_row = QtWidgets.QHBoxLayout()
    tile_highlight_color_input = QtWidgets.QLineEdit(constants.DEFAULT_TILE_HIGHLIGHT_COLOR)
    tile_highlight_color_input.setObjectName(constants.WIDGET_TILE_HIGHLIGHT_COLOR_INPUT)
    widgets[constants.WIDGET_TILE_HIGHLIGHT_COLOR_INPUT] = tile_highlight_color_input
    highlight_color_row.addWidget(tile_highlight_color_input, 1)

    tile_highlight_color_preview = QtWidgets.QLabel()
    tile_highlight_color_preview.setObjectName(constants.WIDGET_TILE_HIGHLIGHT_COLOR_PREVIEW)
    tile_highlight_color_preview.setFixedSize(28, 18)
    tile_highlight_color_preview.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
    widgets[constants.WIDGET_TILE_HIGHLIGHT_COLOR_PREVIEW] = tile_highlight_color_preview
    highlight_color_row.addWidget(tile_highlight_color_preview)

    tile_highlight_color_button = QtWidgets.QPushButton("Choose Color")
    tile_highlight_color_button.setObjectName(constants.WIDGET_TILE_HIGHLIGHT_COLOR_BUTTON)
    widgets[constants.WIDGET_TILE_HIGHLIGHT_COLOR_BUTTON] = tile_highlight_color_button
    highlight_color_row.addWidget(tile_highlight_color_button)
    appearance_layout.addLayout(highlight_color_row, 9, 1, 1, 2)

    appearance_layout.addWidget(QtWidgets.QLabel("Preview Background:"), 10, 0)
    preview_bg_row = QtWidgets.QHBoxLayout()
    icon_preview_bg_input = QtWidgets.QLineEdit(constants.DEFAULT_ICON_PREVIEW_BACKGROUND_COLOR)
    icon_preview_bg_input.setObjectName(constants.WIDGET_ICON_PREVIEW_BACKGROUND_COLOR_INPUT)
    widgets[constants.WIDGET_ICON_PREVIEW_BACKGROUND_COLOR_INPUT] = icon_preview_bg_input
    preview_bg_row.addWidget(icon_preview_bg_input, 1)

    icon_preview_bg_swatch = QtWidgets.QLabel()
    icon_preview_bg_swatch.setObjectName(constants.WIDGET_ICON_PREVIEW_BACKGROUND_COLOR_PREVIEW)
    icon_preview_bg_swatch.setFixedSize(28, 18)
    icon_preview_bg_swatch.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
    widgets[constants.WIDGET_ICON_PREVIEW_BACKGROUND_COLOR_PREVIEW] = icon_preview_bg_swatch
    preview_bg_row.addWidget(icon_preview_bg_swatch)

    icon_preview_bg_button = QtWidgets.QPushButton("Choose Color")
    icon_preview_bg_button.setObjectName(constants.WIDGET_ICON_PREVIEW_BACKGROUND_COLOR_BUTTON)
    widgets[constants.WIDGET_ICON_PREVIEW_BACKGROUND_COLOR_BUTTON] = icon_preview_bg_button
    preview_bg_row.addWidget(icon_preview_bg_button)
    appearance_layout.addLayout(preview_bg_row, 10, 1, 1, 2)

    appearance_layout.addWidget(QtWidgets.QLabel("Live Preview:"), 11, 0)
    icon_size_preview = IconSizeLivePreview()
    icon_size_preview.setObjectName(constants.WIDGET_ICON_SIZE_LIVE_PREVIEW)
    widgets[constants.WIDGET_ICON_SIZE_LIVE_PREVIEW] = icon_size_preview
    appearance_layout.addWidget(icon_size_preview, 11, 1, 1, 2)

    appearance_hint = QtWidgets.QLabel(
        "Font size, tile size, and inner paddings automatically follow the selected icon size."
    )
    appearance_hint.setWordWrap(True)
    appearance_layout.addWidget(appearance_hint, 12, 0, 1, 3)
    return appearance_group


def build_ffmpeg_group(widgets: Dict[str, QtWidgets.QWidget]) -> QtWidgets.QGroupBox:
    ffmpeg_group = QtWidgets.QGroupBox("FFmpeg")
    ffmpeg_layout = QtWidgets.QGridLayout(ffmpeg_group)
    ffmpeg_layout.setColumnStretch(1, 1)

    ffmpeg_layout.addWidget(QtWidgets.QLabel("Detected Source:"), 0, 0)
    source_value = QtWidgets.QLabel("Detecting...")
    source_value.setObjectName(constants.WIDGET_FFMPEG_SOURCE_VALUE)
    source_value.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
    widgets[constants.WIDGET_FFMPEG_SOURCE_VALUE] = source_value
    ffmpeg_layout.addWidget(source_value, 0, 1, 1, 2)

    ffmpeg_layout.addWidget(QtWidgets.QLabel("Resolved Path:"), 1, 0)
    resolved_path_value = QtWidgets.QLineEdit()
    resolved_path_value.setObjectName(constants.WIDGET_FFMPEG_RESOLVED_PATH_VALUE)
    resolved_path_value.setReadOnly(True)
    widgets[constants.WIDGET_FFMPEG_RESOLVED_PATH_VALUE] = resolved_path_value
    ffmpeg_layout.addWidget(resolved_path_value, 1, 1, 1, 2)

    ffmpeg_layout.addWidget(QtWidgets.QLabel("Manual Path:"), 2, 0)
    manual_path_row = QtWidgets.QHBoxLayout()
    manual_path_input = QtWidgets.QLineEdit()
    manual_path_input.setObjectName(constants.WIDGET_FFMPEG_MANUAL_PATH_INPUT)
    manual_path_input.setPlaceholderText(r"Optional: C:\...\ffmpeg.exe")
    widgets[constants.WIDGET_FFMPEG_MANUAL_PATH_INPUT] = manual_path_input
    manual_path_row.addWidget(manual_path_input, 1)

    manual_path_button = QtWidgets.QPushButton("Browse")
    manual_path_button.setObjectName(constants.WIDGET_FFMPEG_MANUAL_PATH_BUTTON)
    widgets[constants.WIDGET_FFMPEG_MANUAL_PATH_BUTTON] = manual_path_button
    manual_path_row.addWidget(manual_path_button)

    rescan_button = QtWidgets.QPushButton("Rescan")
    rescan_button.setObjectName(constants.WIDGET_FFMPEG_RESCAN_BUTTON)
    widgets[constants.WIDGET_FFMPEG_RESCAN_BUTTON] = rescan_button
    manual_path_row.addWidget(rescan_button)
    ffmpeg_layout.addLayout(manual_path_row, 2, 1, 1, 2)

    ffmpeg_hint = QtWidgets.QLabel(
        "Detection order: environment override (TOOLBOX_FFMPEG_PATH), manual path, "
        "system install (PATH/common locations), then bundled internal ffmpeg."
    )
    ffmpeg_hint.setWordWrap(True)
    ffmpeg_layout.addWidget(ffmpeg_hint, 3, 0, 1, 3)
    return ffmpeg_group


def build_grid_group(widgets: Dict[str, QtWidgets.QWidget]) -> QtWidgets.QGroupBox:
    grid_group = QtWidgets.QGroupBox("Grid")
    grid_layout = QtWidgets.QGridLayout(grid_group)
    grid_layout.setColumnStretch(1, 1)

    grid_layout.addWidget(QtWidgets.QLabel("Horizontal Spacing:"), 0, 0)
    grid_x_slider = NoWheelSlider(QtCore.Qt.Orientation.Horizontal)
    grid_x_slider.setObjectName(constants.WIDGET_GRID_SPACING_X_SLIDER)
    grid_x_slider.setRange(constants.MIN_GRID_SPACING, constants.MAX_GRID_SPACING)
    grid_x_slider.setSingleStep(2)
    grid_x_slider.setPageStep(8)
    widgets[constants.WIDGET_GRID_SPACING_X_SLIDER] = grid_x_slider
    grid_layout.addWidget(grid_x_slider, 0, 1)

    grid_x_value = QtWidgets.QLabel(str(constants.DEFAULT_GRID_SPACING_X))
    grid_x_value.setObjectName(constants.WIDGET_GRID_SPACING_X_VALUE)
    grid_x_value.setMinimumWidth(40)
    widgets[constants.WIDGET_GRID_SPACING_X_VALUE] = grid_x_value
    grid_layout.addWidget(grid_x_value, 0, 2)

    grid_layout.addWidget(QtWidgets.QLabel("Vertical Spacing:"), 1, 0)
    grid_y_slider = NoWheelSlider(QtCore.Qt.Orientation.Horizontal)
    grid_y_slider.setObjectName(constants.WIDGET_GRID_SPACING_Y_SLIDER)
    grid_y_slider.setRange(constants.MIN_GRID_SPACING, constants.MAX_GRID_SPACING)
    grid_y_slider.setSingleStep(2)
    grid_y_slider.setPageStep(8)
    widgets[constants.WIDGET_GRID_SPACING_Y_SLIDER] = grid_y_slider
    grid_layout.addWidget(grid_y_slider, 1, 1)

    grid_y_value = QtWidgets.QLabel(str(constants.DEFAULT_GRID_SPACING_Y))
    grid_y_value.setObjectName(constants.WIDGET_GRID_SPACING_Y_VALUE)
    grid_y_value.setMinimumWidth(40)
    widgets[constants.WIDGET_GRID_SPACING_Y_VALUE] = grid_y_value
    grid_layout.addWidget(grid_y_value, 1, 2)

    grid_layout.addWidget(QtWidgets.QLabel("Auto-Compaction:"), 2, 0)
    auto_compact_left_checkbox = QtWidgets.QCheckBox("Auto-compact icons to the left")
    auto_compact_left_checkbox.setObjectName(constants.WIDGET_AUTO_COMPACT_LEFT_CHECKBOX)
    auto_compact_left_checkbox.setChecked(constants.DEFAULT_AUTO_COMPACT_LEFT)
    widgets[constants.WIDGET_AUTO_COMPACT_LEFT_CHECKBOX] = auto_compact_left_checkbox
    grid_layout.addWidget(auto_compact_left_checkbox, 2, 1, 1, 2)

    grid_hint = QtWidgets.QLabel(
        "Tiles remain freely movable and always snap to the active grid when released. "
        "To insert a dragged tile between existing tiles in a row, enable "
        "'Auto-compact icons to the left'."
    )
    grid_hint.setWordWrap(True)
    grid_layout.addWidget(grid_hint, 3, 0, 1, 3)
    return grid_group


def build_section_separator_group(widgets: Dict[str, QtWidgets.QWidget]) -> QtWidgets.QGroupBox:
    separator_group = QtWidgets.QGroupBox("Section Separator")
    separator_layout = QtWidgets.QGridLayout(separator_group)
    separator_layout.setColumnStretch(1, 1)

    separator_layout.addWidget(QtWidgets.QLabel("Header Size:"), 0, 0)
    section_font_slider = NoWheelSlider(QtCore.Qt.Orientation.Horizontal)
    section_font_slider.setObjectName(constants.WIDGET_SECTION_FONT_SIZE_SLIDER)
    section_font_slider.setRange(constants.MIN_SECTION_FONT_SIZE, constants.MAX_SECTION_FONT_SIZE)
    widgets[constants.WIDGET_SECTION_FONT_SIZE_SLIDER] = section_font_slider
    separator_layout.addWidget(section_font_slider, 0, 1)

    section_font_value = QtWidgets.QLabel(str(constants.DEFAULT_SECTION_FONT_SIZE))
    section_font_value.setObjectName(constants.WIDGET_SECTION_FONT_SIZE_VALUE)
    section_font_value.setMinimumWidth(40)
    widgets[constants.WIDGET_SECTION_FONT_SIZE_VALUE] = section_font_value
    separator_layout.addWidget(section_font_value, 0, 2)

    separator_layout.addWidget(QtWidgets.QLabel("Line Thickness:"), 1, 0)
    section_line_slider = NoWheelSlider(QtCore.Qt.Orientation.Horizontal)
    section_line_slider.setObjectName(constants.WIDGET_SECTION_LINE_THICKNESS_SLIDER)
    section_line_slider.setRange(
        constants.MIN_SECTION_LINE_THICKNESS, constants.MAX_SECTION_LINE_THICKNESS
    )
    widgets[constants.WIDGET_SECTION_LINE_THICKNESS_SLIDER] = section_line_slider
    separator_layout.addWidget(section_line_slider, 1, 1)

    section_line_value = QtWidgets.QLabel(str(constants.DEFAULT_SECTION_LINE_THICKNESS))
    section_line_value.setObjectName(constants.WIDGET_SECTION_LINE_THICKNESS_VALUE)
    section_line_value.setMinimumWidth(40)
    widgets[constants.WIDGET_SECTION_LINE_THICKNESS_VALUE] = section_line_value
    separator_layout.addWidget(section_line_value, 1, 2)

    separator_layout.addWidget(QtWidgets.QLabel("Gap Above (px):"), 2, 0)
    section_gap_above_spinbox = NoWheelSpinBox()
    section_gap_above_spinbox.setObjectName(constants.WIDGET_SECTION_GAP_ABOVE_SPINBOX)
    section_gap_above_spinbox.setRange(
        constants.MIN_SECTION_PROTECTED_GAP_ABOVE, constants.MAX_SECTION_PROTECTED_GAP_ABOVE
    )
    section_gap_above_spinbox.setSingleStep(2)
    section_gap_above_spinbox.setSuffix(" px")
    section_gap_above_spinbox.setValue(constants.DEFAULT_SECTION_PROTECTED_GAP_ABOVE)
    widgets[constants.WIDGET_SECTION_GAP_ABOVE_SPINBOX] = section_gap_above_spinbox
    separator_layout.addWidget(section_gap_above_spinbox, 2, 1, 1, 2)

    separator_layout.addWidget(QtWidgets.QLabel("Gap Below (px):"), 3, 0)
    section_gap_below_spinbox = NoWheelSpinBox()
    section_gap_below_spinbox.setObjectName(constants.WIDGET_SECTION_GAP_BELOW_SPINBOX)
    section_gap_below_spinbox.setRange(
        constants.MIN_SECTION_PROTECTED_GAP_BELOW, constants.MAX_SECTION_PROTECTED_GAP_BELOW
    )
    section_gap_below_spinbox.setSingleStep(2)
    section_gap_below_spinbox.setSuffix(" px")
    section_gap_below_spinbox.setValue(constants.DEFAULT_SECTION_PROTECTED_GAP_BELOW)
    widgets[constants.WIDGET_SECTION_GAP_BELOW_SPINBOX] = section_gap_below_spinbox
    separator_layout.addWidget(section_gap_below_spinbox, 3, 1, 1, 2)
    widgets[constants.WIDGET_SECTION_GAP_SPINBOX] = section_gap_below_spinbox

    separator_layout.addWidget(QtWidgets.QLabel("Line Color:"), 4, 0)
    color_row = QtWidgets.QHBoxLayout()
    section_line_color_input = QtWidgets.QLineEdit(constants.DEFAULT_SECTION_LINE_COLOR)
    section_line_color_input.setObjectName(constants.WIDGET_SECTION_LINE_COLOR_INPUT)
    widgets[constants.WIDGET_SECTION_LINE_COLOR_INPUT] = section_line_color_input
    color_row.addWidget(section_line_color_input, 1)

    color_preview = QtWidgets.QLabel()
    color_preview.setObjectName(constants.WIDGET_SECTION_LINE_COLOR_PREVIEW)
    color_preview.setFixedSize(28, 18)
    color_preview.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
    widgets[constants.WIDGET_SECTION_LINE_COLOR_PREVIEW] = color_preview
    color_row.addWidget(color_preview)

    color_button = QtWidgets.QPushButton("Choose Color")
    color_button.setObjectName(constants.WIDGET_SECTION_LINE_COLOR_BUTTON)
    widgets[constants.WIDGET_SECTION_LINE_COLOR_BUTTON] = color_button
    color_row.addWidget(color_button)
    separator_layout.addLayout(color_row, 4, 1, 1, 2)

    separator_layout.addWidget(QtWidgets.QLabel("Live Preview:"), 5, 0)
    section_preview = SectionSeparatorLivePreview()
    section_preview.setObjectName(constants.WIDGET_SECTION_SEPARATOR_LIVE_PREVIEW)
    widgets[constants.WIDGET_SECTION_SEPARATOR_LIVE_PREVIEW] = section_preview
    separator_layout.addWidget(section_preview, 5, 1, 1, 2)

    separator_hint = QtWidgets.QLabel(
        "Separators remain detached. You can tune the protected spacing above/below and line color."
    )
    separator_hint.setWordWrap(True)
    separator_layout.addWidget(separator_hint, 6, 0, 1, 3)
    return separator_group


def build_section_colors_group(widgets: Dict[str, QtWidgets.QWidget]) -> QtWidgets.QGroupBox:
    section_colors_group = QtWidgets.QGroupBox("Section Colors (All Tabs)")
    section_colors_layout = QtWidgets.QVBoxLayout(section_colors_group)
    section_colors_layout.setSpacing(8)

    section_colors_hint = QtWidgets.QLabel(
        "All section separators from all toolbox tabs. "
        "Select one to edit it, or use bulk actions for all separators/titles."
    )
    section_colors_hint.setWordWrap(True)
    section_colors_layout.addWidget(section_colors_hint)

    section_color_list = QtWidgets.QListWidget()
    section_color_list.setObjectName(constants.WIDGET_SECTION_COLOR_LIST)
    section_color_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
    section_color_list.setAlternatingRowColors(True)
    widgets[constants.WIDGET_SECTION_COLOR_LIST] = section_color_list
    section_colors_layout.addWidget(section_color_list)

    selected_section_group = QtWidgets.QGroupBox("Selected Separator")
    selected_section_layout = QtWidgets.QGridLayout(selected_section_group)
    selected_section_layout.setColumnStretch(1, 1)

    selected_section_layout.addWidget(QtWidgets.QLabel("Line Color:"), 0, 0)
    selected_line_row = QtWidgets.QHBoxLayout()
    selected_line_input = QtWidgets.QLineEdit(constants.DEFAULT_SECTION_LINE_COLOR)
    selected_line_input.setObjectName(constants.WIDGET_SECTION_SELECTED_LINE_COLOR_INPUT)
    widgets[constants.WIDGET_SECTION_SELECTED_LINE_COLOR_INPUT] = selected_line_input
    selected_line_row.addWidget(selected_line_input, 1)

    selected_line_preview = QtWidgets.QLabel()
    selected_line_preview.setObjectName(constants.WIDGET_SECTION_SELECTED_LINE_COLOR_PREVIEW)
    selected_line_preview.setFixedSize(28, 18)
    selected_line_preview.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
    widgets[constants.WIDGET_SECTION_SELECTED_LINE_COLOR_PREVIEW] = selected_line_preview
    selected_line_row.addWidget(selected_line_preview)

    selected_line_button = QtWidgets.QPushButton("Choose")
    selected_line_button.setObjectName(constants.WIDGET_SECTION_SELECTED_LINE_COLOR_BUTTON)
    widgets[constants.WIDGET_SECTION_SELECTED_LINE_COLOR_BUTTON] = selected_line_button
    selected_line_row.addWidget(selected_line_button)

    selected_line_apply_button = QtWidgets.QPushButton("Apply to Selected")
    selected_line_apply_button.setObjectName(constants.BUTTON_SECTION_APPLY_SELECTED_LINE_COLOR)
    widgets[constants.BUTTON_SECTION_APPLY_SELECTED_LINE_COLOR] = selected_line_apply_button
    selected_line_row.addWidget(selected_line_apply_button)
    selected_section_layout.addLayout(selected_line_row, 0, 1)

    selected_section_layout.addWidget(QtWidgets.QLabel("Title Color:"), 1, 0)
    selected_title_row = QtWidgets.QHBoxLayout()
    selected_title_input = QtWidgets.QLineEdit("(default)")
    selected_title_input.setObjectName(constants.WIDGET_SECTION_SELECTED_TITLE_COLOR_INPUT)
    widgets[constants.WIDGET_SECTION_SELECTED_TITLE_COLOR_INPUT] = selected_title_input
    selected_title_row.addWidget(selected_title_input, 1)

    selected_title_preview = QtWidgets.QLabel()
    selected_title_preview.setObjectName(constants.WIDGET_SECTION_SELECTED_TITLE_COLOR_PREVIEW)
    selected_title_preview.setFixedSize(28, 18)
    selected_title_preview.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
    widgets[constants.WIDGET_SECTION_SELECTED_TITLE_COLOR_PREVIEW] = selected_title_preview
    selected_title_row.addWidget(selected_title_preview)

    selected_title_button = QtWidgets.QPushButton("Choose")
    selected_title_button.setObjectName(constants.WIDGET_SECTION_SELECTED_TITLE_COLOR_BUTTON)
    widgets[constants.WIDGET_SECTION_SELECTED_TITLE_COLOR_BUTTON] = selected_title_button
    selected_title_row.addWidget(selected_title_button)

    selected_title_apply_button = QtWidgets.QPushButton("Apply to Selected")
    selected_title_apply_button.setObjectName(constants.BUTTON_SECTION_APPLY_SELECTED_TITLE_COLOR)
    widgets[constants.BUTTON_SECTION_APPLY_SELECTED_TITLE_COLOR] = selected_title_apply_button
    selected_title_row.addWidget(selected_title_apply_button)
    selected_section_layout.addLayout(selected_title_row, 1, 1)

    section_colors_layout.addWidget(selected_section_group)

    bulk_colors_group = QtWidgets.QGroupBox("Bulk Colors")
    bulk_colors_layout = QtWidgets.QGridLayout(bulk_colors_group)
    bulk_colors_layout.setColumnStretch(1, 1)

    bulk_colors_layout.addWidget(QtWidgets.QLabel("All Separator Lines:"), 0, 0)
    all_line_row = QtWidgets.QHBoxLayout()
    all_line_input = QtWidgets.QLineEdit(constants.DEFAULT_SECTION_LINE_COLOR)
    all_line_input.setObjectName(constants.WIDGET_SECTION_ALL_LINE_COLOR_INPUT)
    widgets[constants.WIDGET_SECTION_ALL_LINE_COLOR_INPUT] = all_line_input
    all_line_row.addWidget(all_line_input, 1)

    all_line_preview = QtWidgets.QLabel()
    all_line_preview.setObjectName(constants.WIDGET_SECTION_ALL_LINE_COLOR_PREVIEW)
    all_line_preview.setFixedSize(28, 18)
    all_line_preview.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
    widgets[constants.WIDGET_SECTION_ALL_LINE_COLOR_PREVIEW] = all_line_preview
    all_line_row.addWidget(all_line_preview)

    all_line_button = QtWidgets.QPushButton("Choose")
    all_line_button.setObjectName(constants.WIDGET_SECTION_ALL_LINE_COLOR_BUTTON)
    widgets[constants.WIDGET_SECTION_ALL_LINE_COLOR_BUTTON] = all_line_button
    all_line_row.addWidget(all_line_button)

    all_line_apply = QtWidgets.QPushButton("Apply to All Separators")
    all_line_apply.setObjectName(constants.BUTTON_SECTION_APPLY_ALL_LINE_COLOR)
    widgets[constants.BUTTON_SECTION_APPLY_ALL_LINE_COLOR] = all_line_apply
    all_line_row.addWidget(all_line_apply)
    bulk_colors_layout.addLayout(all_line_row, 0, 1)

    line_quick_row = QtWidgets.QHBoxLayout()
    line_quick_row.addWidget(QtWidgets.QLabel("Quick:"))
    quick_line_buttons: list[QtWidgets.QPushButton] = []
    for object_name, text, color_value in (
        (constants.BUTTON_SECTION_QUICK_ALL_LINE_DEFAULT, "Default", ""),
        (constants.BUTTON_SECTION_QUICK_ALL_LINE_GRAY, "Gray", "#444a57"),
        (constants.BUTTON_SECTION_QUICK_ALL_LINE_BLUE, "Blue", "#3f72af"),
        (constants.BUTTON_SECTION_QUICK_ALL_LINE_GREEN, "Green", "#2ecc71"),
        (constants.BUTTON_SECTION_QUICK_ALL_LINE_RED, "Red", "#e74c3c"),
    ):
        button = QtWidgets.QPushButton(text)
        button.setObjectName(object_name)
        button.setProperty("quick_color", color_value)
        if color_value:
            button.setStyleSheet(f"border: 1px solid {color_value};")
        widgets[object_name] = button
        quick_line_buttons.append(button)
        line_quick_row.addWidget(button)
    line_quick_row.addStretch(1)
    bulk_colors_layout.addLayout(line_quick_row, 1, 1)

    bulk_colors_layout.addWidget(QtWidgets.QLabel("All Separator Titles:"), 2, 0)
    all_title_row = QtWidgets.QHBoxLayout()
    all_title_input = QtWidgets.QLineEdit("(default)")
    all_title_input.setObjectName(constants.WIDGET_SECTION_ALL_TITLE_COLOR_INPUT)
    widgets[constants.WIDGET_SECTION_ALL_TITLE_COLOR_INPUT] = all_title_input
    all_title_row.addWidget(all_title_input, 1)

    all_title_preview = QtWidgets.QLabel()
    all_title_preview.setObjectName(constants.WIDGET_SECTION_ALL_TITLE_COLOR_PREVIEW)
    all_title_preview.setFixedSize(28, 18)
    all_title_preview.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
    widgets[constants.WIDGET_SECTION_ALL_TITLE_COLOR_PREVIEW] = all_title_preview
    all_title_row.addWidget(all_title_preview)

    all_title_button = QtWidgets.QPushButton("Choose")
    all_title_button.setObjectName(constants.WIDGET_SECTION_ALL_TITLE_COLOR_BUTTON)
    widgets[constants.WIDGET_SECTION_ALL_TITLE_COLOR_BUTTON] = all_title_button
    all_title_row.addWidget(all_title_button)

    all_title_apply = QtWidgets.QPushButton("Apply to All Titles")
    all_title_apply.setObjectName(constants.BUTTON_SECTION_APPLY_ALL_TITLE_COLOR)
    widgets[constants.BUTTON_SECTION_APPLY_ALL_TITLE_COLOR] = all_title_apply
    all_title_row.addWidget(all_title_apply)
    bulk_colors_layout.addLayout(all_title_row, 2, 1)

    title_quick_row = QtWidgets.QHBoxLayout()
    title_quick_row.addWidget(QtWidgets.QLabel("Quick:"))
    quick_title_buttons: list[QtWidgets.QPushButton] = []
    for object_name, text, color_value in (
        (constants.BUTTON_SECTION_QUICK_ALL_TITLE_DEFAULT, "Default", ""),
        (constants.BUTTON_SECTION_QUICK_ALL_TITLE_WHITE, "White", "#f5f5f5"),
        (constants.BUTTON_SECTION_QUICK_ALL_TITLE_AMBER, "Amber", "#ffbf00"),
        (constants.BUTTON_SECTION_QUICK_ALL_TITLE_CYAN, "Cyan", "#00d2ff"),
        (constants.BUTTON_SECTION_QUICK_ALL_TITLE_RED, "Red", "#ff4d4f"),
    ):
        button = QtWidgets.QPushButton(text)
        button.setObjectName(object_name)
        button.setProperty("quick_color", color_value)
        if color_value:
            button.setStyleSheet(f"border: 1px solid {color_value};")
        widgets[object_name] = button
        quick_title_buttons.append(button)
        title_quick_row.addWidget(button)
    title_quick_row.addStretch(1)
    bulk_colors_layout.addLayout(title_quick_row, 3, 1)

    all_quick_buttons = quick_line_buttons + quick_title_buttons
    if all_quick_buttons:
        min_width = max(button.sizeHint().width() for button in all_quick_buttons)
        for button in all_quick_buttons:
            button.setMinimumWidth(min_width)

    section_colors_layout.addWidget(bulk_colors_group)
    return section_colors_group


def build_tabs_group(widgets: Dict[str, QtWidgets.QWidget]) -> QtWidgets.QGroupBox:
    tabs_group = QtWidgets.QGroupBox("Manage Tabs")
    tabs_layout = QtWidgets.QVBoxLayout(tabs_group)
    tabs_layout.setSpacing(8)

    tabs_hint = QtWidgets.QLabel("Manage order and visibility here. 'Settings' always stays visible.")
    tabs_hint.setWordWrap(True)
    tabs_layout.addWidget(tabs_hint)

    tab_manager_list = QtWidgets.QListWidget()
    tab_manager_list.setObjectName(constants.WIDGET_TAB_MANAGER_LIST)
    tab_manager_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
    tab_manager_list.setAlternatingRowColors(True)
    tab_manager_list.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    widgets[constants.WIDGET_TAB_MANAGER_LIST] = tab_manager_list
    tabs_layout.addWidget(tab_manager_list)

    tab_buttons = QtWidgets.QHBoxLayout()
    move_up_button = QtWidgets.QPushButton("Move Up")
    move_up_button.setObjectName(constants.BUTTON_TAB_MOVE_UP)
    widgets[constants.BUTTON_TAB_MOVE_UP] = move_up_button
    tab_buttons.addWidget(move_up_button)

    move_down_button = QtWidgets.QPushButton("Move Down")
    move_down_button.setObjectName(constants.BUTTON_TAB_MOVE_DOWN)
    widgets[constants.BUTTON_TAB_MOVE_DOWN] = move_down_button
    tab_buttons.addWidget(move_down_button)
    tab_buttons.addStretch(1)
    tabs_layout.addLayout(tab_buttons)
    return tabs_group


def build_maintenance_group(widgets: Dict[str, QtWidgets.QWidget]) -> QtWidgets.QGroupBox:
    diagnostics_group = QtWidgets.QGroupBox("Maintenance")
    diagnostics_layout = QtWidgets.QVBoxLayout(diagnostics_group)
    diagnostics_layout.setSpacing(8)

    diagnostics_hint = QtWidgets.QLabel(
        "Checks all toolbox tabs for missing or unreachable app/folder paths."
    )
    diagnostics_hint.setWordWrap(True)
    diagnostics_layout.addWidget(diagnostics_hint)

    check_broken_entries_button = QtWidgets.QPushButton("Check Broken Entries")
    check_broken_entries_button.setObjectName(constants.BUTTON_CHECK_BROKEN_ENTRIES)
    widgets[constants.BUTTON_CHECK_BROKEN_ENTRIES] = check_broken_entries_button
    diagnostics_layout.addWidget(
        check_broken_entries_button, 0, QtCore.Qt.AlignmentFlag.AlignLeft
    )
    return diagnostics_group


def build_backup_group(widgets: Dict[str, QtWidgets.QWidget]) -> QtWidgets.QGroupBox:
    backup_group = QtWidgets.QGroupBox("Export / Import")
    backup_layout = QtWidgets.QVBoxLayout(backup_group)
    backup_layout.setSpacing(8)

    backup_hint = QtWidgets.QLabel(
        "Saves tabs, entries (including positions), and appearance settings to a JSON file."
    )
    backup_hint.setWordWrap(True)
    backup_layout.addWidget(backup_hint)

    backup_buttons = QtWidgets.QHBoxLayout()
    export_button = QtWidgets.QPushButton("Export to JSON")
    export_button.setObjectName(constants.WIDGET_EXPORT_PROFILE_BUTTON)
    widgets[constants.WIDGET_EXPORT_PROFILE_BUTTON] = export_button
    backup_buttons.addWidget(export_button)

    import_button = QtWidgets.QPushButton("Import from JSON")
    import_button.setObjectName(constants.WIDGET_IMPORT_PROFILE_BUTTON)
    widgets[constants.WIDGET_IMPORT_PROFILE_BUTTON] = import_button
    backup_buttons.addWidget(import_button)
    backup_buttons.addStretch(1)
    backup_layout.addLayout(backup_buttons)
    return backup_group


def build_apply_row(widgets: Dict[str, QtWidgets.QWidget]) -> QtWidgets.QHBoxLayout:
    apply_row = QtWidgets.QHBoxLayout()
    apply_row.addStretch(1)
    apply_settings_button = QtWidgets.QPushButton("Save & Apply")
    apply_settings_button.setObjectName(constants.BUTTON_APPLY_SETTINGS)
    widgets[constants.BUTTON_APPLY_SETTINGS] = apply_settings_button
    apply_row.addWidget(apply_settings_button)
    return apply_row
