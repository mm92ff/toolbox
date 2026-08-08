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
    build_system_tray_group,
    build_tabs_group,
    build_file_associations_group,
)


def create_settings_tab() -> Tuple[QtWidgets.QWidget, Dict[str, QtWidgets.QWidget]]:
    """Build and return the Settings tab widget tree and named widget registry."""
    widgets: Dict[str, QtWidgets.QWidget] = {}
    tab = QtWidgets.QWidget()
    root_layout = QtWidgets.QVBoxLayout(tab)
    root_layout.setContentsMargins(14, 14, 14, 14)
    root_layout.setSpacing(14)

    sub_tabs = QtWidgets.QTabWidget()
    root_layout.addWidget(sub_tabs)

    def create_scrollable_tab(groups) -> QtWidgets.QWidget:
        t = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(t)
        layout.setContentsMargins(0, 0, 0, 0)

        sa = QtWidgets.QScrollArea()
        sa.setWidgetResizable(True)
        sa.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        layout.addWidget(sa)

        cw = QtWidgets.QWidget()
        cl = QtWidgets.QVBoxLayout(cw)
        cl.setContentsMargins(14, 14, 14, 14)
        cl.setSpacing(14)
        sa.setWidget(cw)

        for g in groups:
            cl.addWidget(g)
        cl.addStretch(1)

        return t

    tab_appearance = create_scrollable_tab([
        build_appearance_group(widgets),
        build_grid_group(widgets),
        build_ffmpeg_group(widgets),
    ])
    sub_tabs.addTab(tab_appearance, "Appearance & Layout")

    tab_sections = create_scrollable_tab([
        build_section_separator_group(widgets),
        build_section_colors_group(widgets),
    ])
    sub_tabs.addTab(tab_sections, "Sections & Colors")

    tab_system = create_scrollable_tab([
        build_system_tray_group(widgets),
        build_tabs_group(widgets),
        build_file_associations_group(widgets),
        build_maintenance_group(widgets),
        build_backup_group(widgets),
    ])
    sub_tabs.addTab(tab_system, "System")

    root_layout.addLayout(build_apply_row(widgets))
    return tab, widgets
