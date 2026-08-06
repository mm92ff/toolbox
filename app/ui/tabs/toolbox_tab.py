#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UI builder for toolbox tabs."""

from __future__ import annotations

from typing import Dict, Tuple

from PySide6 import QtCore, QtWidgets

from app import constants
from app.canvas.toolbox_canvas import ToolboxCanvas


def create_toolbox_tab() -> Tuple[QtWidgets.QWidget, Dict[str, QtWidgets.QWidget]]:
    """Build and return one toolbox tab (layout plus named child widgets)."""
    widgets: Dict[str, QtWidgets.QWidget] = {}
    tab = QtWidgets.QWidget()
    layout = QtWidgets.QVBoxLayout(tab)
    layout.setContentsMargins(0, 0, 0, 0)

    splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Vertical)
    splitter.setObjectName(constants.WIDGET_TOOLBOX_SPLITTER)
    widgets[constants.WIDGET_TOOLBOX_SPLITTER] = splitter

    # Breadcrumb bar for folder browsing (hidden by default)
    breadcrumb_bar = QtWidgets.QWidget()
    breadcrumb_bar.setObjectName("breadcrumb_bar")
    breadcrumb_bar.setVisible(False)
    breadcrumb_bar.setFixedHeight(36)
    breadcrumb_layout = QtWidgets.QHBoxLayout(breadcrumb_bar)
    breadcrumb_layout.setContentsMargins(8, 4, 8, 4)
    breadcrumb_layout.setSpacing(6)
    
    back_btn = QtWidgets.QToolButton()
    back_btn.setObjectName("btn_browse_back")
    back_btn.setText("← Zurück")
    back_btn.setAutoRaise(True)
    back_btn.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
    breadcrumb_layout.addWidget(back_btn)
    
    breadcrumb_sep = QtWidgets.QFrame()
    breadcrumb_sep.setFrameShape(QtWidgets.QFrame.Shape.VLine)
    breadcrumb_sep.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
    breadcrumb_layout.addWidget(breadcrumb_sep)
    
    breadcrumb_path_label = QtWidgets.QLabel()
    breadcrumb_path_label.setObjectName("lbl_breadcrumb_path")
    breadcrumb_path_label.setTextFormat(QtCore.Qt.TextFormat.PlainText)
    breadcrumb_layout.addWidget(breadcrumb_path_label, 1)
    
    breadcrumb_layout.addStretch()
    widgets["breadcrumb_bar"] = breadcrumb_bar
    widgets["btn_browse_back"] = back_btn
    widgets["lbl_breadcrumb_path"] = breadcrumb_path_label

    # Keep legacy controls available for controller compatibility,
    # but remove the visual top/bottom panels from the tab UI.
    top_panel = QtWidgets.QWidget(tab)
    top_panel.setObjectName(constants.WIDGET_TOP_PANEL)
    top_panel.setVisible(False)
    top_layout = QtWidgets.QVBoxLayout(top_panel)
    top_layout.setContentsMargins(12, 12, 12, 12)
    top_layout.setSpacing(10)

    search_row = QtWidgets.QHBoxLayout()
    search_row.addWidget(QtWidgets.QLabel("Search:"))
    search_input = QtWidgets.QLineEdit()
    search_input.setObjectName(constants.WIDGET_SEARCH_INPUT)
    search_input.setPlaceholderText("Filter apps or sections ...")
    search_input.setVisible(False)
    widgets[constants.WIDGET_SEARCH_INPUT] = search_input
    search_row.addWidget(search_input, 1)
    top_layout.addLayout(search_row)

    drop_zone = QtWidgets.QFrame()
    drop_zone.setObjectName(constants.WIDGET_DROP_ZONE)
    drop_zone.setMinimumHeight(92)
    drop_zone.setVisible(False)
    drop_zone.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
    drop_zone.setStyleSheet("""
        QFrame#drop_zone {
            border: 1px dashed palette(mid);
            border-radius: 10px;
            background: rgba(255, 255, 255, 0.03);
        }
        """)
    drop_layout = QtWidgets.QVBoxLayout(drop_zone)
    drop_label = QtWidgets.QLabel("Drop files or folders here\n(all file types are supported)")
    drop_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    drop_layout.addStretch(1)
    drop_layout.addWidget(drop_label)
    drop_layout.addStretch(1)
    widgets[constants.WIDGET_DROP_ZONE] = drop_zone
    top_layout.addWidget(drop_zone)

    button_row = QtWidgets.QHBoxLayout()
    for key, text in (
        (constants.BUTTON_ADD_TOOL, "Add Apps"),
        (constants.BUTTON_ADD_SECTION, "Add Section"),
        (constants.BUTTON_LAUNCH_TOOL, "Launch"),
        (constants.BUTTON_REMOVE_TOOL, "Remove"),
        (constants.BUTTON_OPEN_CONFIG, "Config Folder"),
    ):
        button = QtWidgets.QPushButton(text)
        button.setObjectName(key)
        button.setVisible(False)
        widgets[key] = button
        button_row.addWidget(button)
    button_row.addStretch(1)
    top_layout.addLayout(button_row)

    canvas = ToolboxCanvas()
    canvas.setObjectName(constants.WIDGET_TOOL_CANVAS)
    widgets[constants.WIDGET_TOOL_CANVAS] = canvas

    bottom_panel = QtWidgets.QWidget(tab)
    bottom_panel.setObjectName(constants.WIDGET_BOTTOM_PANEL)
    bottom_panel.setVisible(False)
    bottom_layout = QtWidgets.QVBoxLayout(bottom_panel)
    bottom_layout.setContentsMargins(12, 10, 12, 10)

    details = QtWidgets.QLabel("No entries yet.")
    details.setObjectName(constants.WIDGET_TOOL_DETAILS)
    details.setVisible(False)
    details.setWordWrap(True)
    details.setMinimumHeight(60)
    details.setFrameShape(QtWidgets.QFrame.Shape.StyledPanel)
    details.setStyleSheet("""
        QLabel#lbl_tool_details {
            border: 1px solid palette(mid);
            border-radius: 10px;
            padding: 10px;
            background: rgba(255, 255, 255, 0.03);
        }
        """)
    widgets[constants.WIDGET_TOOL_DETAILS] = details
    bottom_layout.addWidget(details)

    splitter.addWidget(canvas)
    splitter.setStretchFactor(0, 1)
    splitter.setHandleWidth(0)

    layout.addWidget(breadcrumb_bar)  # add before splitter
    layout.addWidget(splitter)
    widgets[constants.WIDGET_TOP_PANEL] = top_panel
    widgets[constants.WIDGET_BOTTOM_PANEL] = bottom_panel
    return tab, widgets
