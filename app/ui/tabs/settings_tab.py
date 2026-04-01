#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UI builder for settings tab."""

from __future__ import annotations

from typing import Dict, Tuple

from PySide6 import QtWidgets

from app.ui.tabs.settings_tab_sections import (
    build_appearance_group,
    build_apply_row,
    build_backup_group,
    build_ffmpeg_group,
    build_grid_group,
    build_maintenance_group,
    build_section_colors_group,
    build_section_separator_group,
    build_tabs_group,
)


def create_settings_tab() -> Tuple[QtWidgets.QWidget, Dict[str, QtWidgets.QWidget]]:
    """Build and return the Settings tab widget tree and named widget registry."""
    widgets: Dict[str, QtWidgets.QWidget] = {}
    tab = QtWidgets.QWidget()
    root_layout = QtWidgets.QVBoxLayout(tab)
    root_layout.setContentsMargins(0, 0, 0, 0)
    root_layout.setSpacing(0)

    scroll_area = QtWidgets.QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
    root_layout.addWidget(scroll_area)

    content_widget = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(content_widget)
    layout.setContentsMargins(14, 14, 14, 14)
    layout.setSpacing(14)
    scroll_area.setWidget(content_widget)

    layout.addWidget(build_appearance_group(widgets))
    layout.addWidget(build_ffmpeg_group(widgets))
    layout.addWidget(build_grid_group(widgets))
    layout.addWidget(build_section_separator_group(widgets))
    layout.addWidget(build_section_colors_group(widgets))
    layout.addWidget(build_tabs_group(widgets))
    layout.addWidget(build_maintenance_group(widgets))
    layout.addWidget(build_backup_group(widgets))
    layout.addLayout(build_apply_row(widgets))
    layout.addStretch(1)
    return tab, widgets
