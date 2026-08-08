#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UI builder for help tab."""

from __future__ import annotations

from typing import Dict, Sequence, Tuple

from PySide6 import QtCore, QtWidgets

from app import constants


def _create_help_section(title: str, points: Sequence[str]) -> QtWidgets.QWidget:
    section = QtWidgets.QWidget()
    section.setObjectName("help_section")
    section_layout = QtWidgets.QVBoxLayout(section)
    section_layout.setContentsMargins(0, 0, 0, 10)
    section_layout.setSpacing(6)
    
    title_label = QtWidgets.QLabel(title)
    title_label.setObjectName("help_section_title")
    title_font = title_label.font()
    title_font.setBold(True)
    title_font.setPointSize(max(10, title_font.pointSize() + 1))
    title_label.setFont(title_font)
    section_layout.addWidget(title_label)
    
    # Use HTML for bullet points
    html_points = "".join(f"<li style='margin-bottom: 4px;'>{point}</li>" for point in points)
    content_label = QtWidgets.QLabel(f"<ul style='margin-top: 4px; margin-bottom: 0px; padding-left: 20px;'>{html_points}</ul>")
    content_label.setWordWrap(True)
    content_label.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse | QtCore.Qt.TextInteractionFlag.LinksAccessibleByMouse)
    section_layout.addWidget(content_label)
    
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
    title.setObjectName("help_main_title")
    title_font = title.font()
    title_font.setBold(True)
    title_font.setPointSize(max(16, title_font.pointSize() + 6))
    title.setFont(title_font)
    header_layout.addWidget(title)

    intro = QtWidgets.QLabel(
        "<i>Current feature overview for the toolbox. "
        "The sections below summarize the main workflows, layout behavior, and settings logic.</i>"
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
                (
                    "On Linux, drop files or URLs directly onto a compatible "
                    ".desktop tile to pass them through %f, %F, %u, or %U."
                ),
                (
                    "Drop on empty canvas space still adds the dropped item as "
                    "a new toolbox tile."
                ),
                "Alternatively, use 'Add Apps' to select apps manually.",
                (
                    "When a folder is open, its breadcrumb bar provides a Symbolgröße "
                    "slider. The value is remembered for that folder; reset restores "
                    "the current global icon size."
                ),
                "Open folders automatically wrap their tiles to the available window width.",
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
                (
                    "When responsive layout is enabled for normal tabs, resizing keeps saved "
                    "positions untouched and manual movement stays disabled until the option "
                    "is switched off."
                ),
                "Dropping a tile directly between two tiles in the same row requires 'Auto-compact icons to the left' to be enabled.",
                "Right-click on empty canvas space to insert grid rows above or below.",
                "Right-click on empty canvas space or a section header to 'Alphabetisch sortieren' (Auto-sort alphabetically).",
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
                    "Right-click a tile to access Launch options, 'Eigenschaften bearbeiten' (Tile Properties), "
                    "or 'Run as administrator'."
                ),
                "In 'Tile Properties', you can set a custom title or custom icon path for a specific tile.",
                (
                    "Default launch options (arguments, working directory, wait, "
                    "window style) can be saved per entry."
                ),
                (
                    "Linux .desktop entries are validated before launch. Toolbox "
                    "shows monitored process failures when available."
                ),
                (
                    "Terminal and D-Bus activated desktop entries are delegated "
                    "to the desktop system; later target failures cannot always be detected."
                ),
                (
                    "Desktop tiles use the Name and Icon declared by the launcher "
                    "when those values can be resolved."
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
                (
                    "Use the '+' button in the top tab bar, or press Ctrl+T, "
                    "to create and open a new toolbox tab."
                ),
                (
                    "Press Ctrl+N to open another synchronized Toolbox window. "
                    "Tabs, entries, settings, and undo/redo are shared, while active "
                    "tab, search, selection, and folder browsing stay window-local."
                ),
                "Tab titles can be renamed via right-click.",
                "Right-click a toolbox tab to open that tab in a new window.",
                "In 'Manage Tabs' you can adjust order and visibility.",
                "The 'Settings' and 'Help' tabs are permanently docked on the right side of the tab bar.",
                "Right-click on empty canvas space to set/reset the background color for the current tab.",
                (
                    "Settings are organized into sub-tabs (Design & Layout, System, Export & Import) "
                    "for easier navigation."
                ),
                (
                    "The System settings control whether the tray icon remains visible and, "
                    "independently, whether closing the last window minimizes Toolbox to the tray."
                ),
                (
                    "System settings also choose whether a second Toolbox start activates "
                    "the last window or creates a new window."
                ),
                (
                    "In the Settings tab, you can fine-tune icon size, tile-title "
                    "font size, grid, responsive wrapping, compaction, separator style, "
                    "and tile colors."
                ),
                "Separator spacing can be adjusted separately with 'Gap Above' and 'Gap Below'.",
                (
                    "Section color manager lists separators from all tabs and supports "
                    "single, bulk, and quick apply actions."
                ),
                "Tile titles that are too long will gracefully elide with '...' and show the full name as a tooltip.",
                "Image preview thumbnails and video preview thumbnails (ffmpeg) can be enabled independently.",
                "Preview mode supports Fit (full image) and Fill (crop).",
                "The Settings tab includes an FFmpeg section showing source/status and the resolved executable path.",
                (
                    "You can download a portable internal FFmpeg directly from Settings if it's missing, "
                    "or set a manual path."
                ),
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
        "Ctrl+Y redoes it, Ctrl+N opens a new window, and Save & Apply commits pending settings changes."
    )
    quick_tips.setWordWrap(True)
    quick_tips.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
    layout.addWidget(quick_tips)
    layout.addStretch(1)

    tab.setStyleSheet("""
        QFrame#help_header {
            background: transparent;
            border-bottom: 1px solid palette(midlight);
            border-radius: 0px;
        }
        QLabel#help_main_title {
            color: palette(highlight);
        }
        QLabel[objectName="help_section_title"] {
            color: palette(highlight);
            padding-bottom: 2px;
            border-bottom: 1px solid palette(midlight);
        }
        QWidget#help_section {
            margin-top: 8px;
            background: transparent;
        }
        """)
    return tab, widgets
