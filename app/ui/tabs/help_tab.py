#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UI builder for help tab."""

from __future__ import annotations

from typing import Dict, Sequence, Tuple

from PySide6 import QtCore, QtWidgets

from app import constants


def _create_help_section(title: str, points: Sequence[str]) -> QtWidgets.QGroupBox:
    section = QtWidgets.QGroupBox(title)
    section.setObjectName("help_section")
    section_layout = QtWidgets.QVBoxLayout(section)
    section_layout.setContentsMargins(12, 10, 12, 10)
    section_layout.setSpacing(6)
    for point in points:
        row = QtWidgets.QLabel(f"• {point}")
        row.setWordWrap(True)
        row.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        section_layout.addWidget(row)
    return section


def create_help_tab() -> Tuple[QtWidgets.QWidget, Dict[str, QtWidgets.QWidget]]:
    """Build and return the Help tab widget tree and named widget registry."""
    widgets: Dict[str, QtWidgets.QWidget] = {}
    tab = QtWidgets.QWidget()
    root_layout = QtWidgets.QVBoxLayout(tab)
    root_layout.setContentsMargins(0, 0, 0, 0)
    root_layout.setSpacing(0)

    scroll_area = QtWidgets.QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_area.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
    root_layout.addWidget(scroll_area)

    content = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(content)
    layout.setContentsMargins(14, 14, 14, 14)
    layout.setSpacing(12)
    scroll_area.setWidget(content)

    header = QtWidgets.QFrame()
    header.setObjectName("help_header")
    header_layout = QtWidgets.QVBoxLayout(header)
    header_layout.setContentsMargins(12, 12, 12, 12)
    header_layout.setSpacing(5)

    title = QtWidgets.QLabel("Toolbox Help")
    title_font = title.font()
    title_font.setBold(True)
    title_font.setPointSize(max(12, title_font.pointSize() + 2))
    title.setFont(title_font)
    header_layout.addWidget(title)

    intro = QtWidgets.QLabel(
        "Current feature overview for the toolbox. "
        "The sections below summarize the main workflows, layout behavior, and settings logic."
    )
    intro.setObjectName(constants.WIDGET_HELP_TEXT)
    intro.setWordWrap(True)
    intro.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
    widgets[constants.WIDGET_HELP_TEXT] = intro
    header_layout.addWidget(intro)
    layout.addWidget(header)

    layout.addWidget(
        _create_help_section(
            "Quick Start",
            (
                "Drag and drop files or folders directly into a toolbox.",
                "Alternatively, use 'Add Apps' to select apps manually.",
                "Use right-click on empty canvas space to add a section at that position.",
                "Launch behavior can be switched globally between single-click and double-click in Settings.",
            ),
        )
    )
    layout.addWidget(
        _create_help_section(
            "Selection and Moving",
            (
                "Hold Shift to select multiple tiles.",
                (
                    "Click and drag with the left mouse button on empty space "
                    "to draw a selection box (icons and headers)."
                ),
                (
                    "If multiple entries are selected, dragging one selected item "
                    "moves the whole group."
                ),
                "Mixed selection (sections + tiles) uses vertical group movement to keep structure stable.",
                "A short hold with left mouse button activates move mode; release snaps back to grid.",
                "Dropping a tile directly between two tiles in the same row requires 'Auto-compact icons to the left' to be enabled.",
                "Right-click on empty canvas space to insert grid rows above or below.",
                "Section drag hints: green means snap-near target, red means tool-conflict zone.",
            ),
        )
    )
    layout.addWidget(
        _create_help_section(
            "Entries and Launch Options",
            (
                "Double-click a section separator to rename its header.",
                (
                    "Right-click a tile for Launch, Launch with parameters, "
                    "and 'Run as administrator'."
                ),
                (
                    "Default launch options (arguments, working directory, wait, "
                    "window style) can be saved per entry."
                ),
                "Use 'Open Path' to jump directly to the corresponding folder.",
                "Delete or Backspace removes the current selection.",
            ),
        )
    )
    layout.addWidget(
        _create_help_section(
            "Separator Spacing and Grid Rules",
            (
                "Separator protection uses two values: 'Gap Above' and 'Gap Below'.",
                "Tiles still snap to the active grid, so visible spacing can change in row-sized steps.",
                (
                    "If a separator is moved into tools, tools are pushed down to keep the "
                    "protected zone clean."
                ),
                "Because of snapping, exact pixel-perfect spacing is not always possible.",
            ),
        )
    )
    layout.addWidget(
        _create_help_section(
            "Tabs, Colors, and Preview",
            (
                "Tab titles can be renamed via right-click.",
                "In 'Manage Tabs' you can adjust order and visibility.",
                "Right-click on empty canvas space to set/reset the background color for the current tab.",
                (
                    "In the Settings tab, you can fine-tune icon size, grid, "
                    "compaction, separator style, and tile colors."
                ),
                "Separator spacing can be adjusted separately with 'Gap Above' and 'Gap Below'.",
                (
                    "Section color manager lists separators from all tabs and supports "
                    "single, bulk, and quick apply actions."
                ),
                "Image preview thumbnails and video preview thumbnails (ffmpeg) can be enabled independently.",
                "Preview mode supports Fit (full image) and Fill (crop).",
                "The Settings tab includes an FFmpeg section showing source/status and the resolved executable path.",
                "You can set a manual ffmpeg.exe path there and use Rescan to refresh detection.",
                "Optional hover preview can show larger image/video thumbnails on mouse-over.",
                "Changes in the Settings tab become active only after 'Save & Apply'.",
                "UI settings are also stored as JSON in the config folder (ui_settings.json).",
            ),
        )
    )
    layout.addWidget(
        _create_help_section(
            "Maintenance",
            (
                (
                    "The maintenance button 'Check Broken Entries' finds orphaned "
                    "paths and can remove them."
                ),
                (
                    "The diagnostics check runs in the background and shows the result "
                    "dialog when finished."
                ),
                "Export/Import saves tabs, entries, and UI settings to/from a JSON profile.",
            ),
        )
    )

    quick_tips = QtWidgets.QLabel(
        "Tips: Shift-click supports multi-select, Ctrl+Z undoes the last toolbox change, "
        "Ctrl+Y redoes it, and Save & Apply commits pending settings changes."
    )
    quick_tips.setWordWrap(True)
    quick_tips.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
    layout.addWidget(quick_tips)
    layout.addStretch(1)

    tab.setStyleSheet("""
        QFrame#help_header {
            border: 1px solid palette(mid);
            border-radius: 8px;
            background: palette(base);
        }
        QGroupBox#help_section {
            margin-top: 10px;
            border: 1px solid palette(mid);
            border-radius: 8px;
            padding-top: 8px;
            background: palette(base);
        }
        QGroupBox#help_section::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px 0 4px;
        }
        """)
    return tab, widgets
