#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""UI composition entrypoint for the toolbox launcher."""

from __future__ import annotations

from typing import Dict, Tuple

from PySide6 import QtWidgets

from app import constants
from app.ui.tabs.help_tab import create_help_tab
from app.ui.tabs.settings_tab import create_settings_tab
from app.ui.tabs.toolbox_tab import create_toolbox_tab as create_toolbox_tab_layout


class UIBuilder:
    """Builds reusable widgets for the main window."""

    @staticmethod
    def create_main_layout() -> Tuple[QtWidgets.QWidget, Dict[str, QtWidgets.QWidget]]:
        widgets: Dict[str, QtWidgets.QWidget] = {}

        central_widget = QtWidgets.QWidget()
        root_layout = QtWidgets.QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        tabs = QtWidgets.QTabWidget()
        tabs.setObjectName(constants.WIDGET_TABS)
        widgets[constants.WIDGET_TABS] = tabs
        root_layout.addWidget(tabs)

        settings_tab, settings_widgets = create_settings_tab()
        settings_tab.setObjectName(constants.WIDGET_SETTINGS_TAB)
        widgets.update(settings_widgets)
        widgets[constants.WIDGET_SETTINGS_TAB] = settings_tab
        tabs.addTab(settings_tab, "Settings")

        help_tab, help_widgets = create_help_tab()
        help_tab.setObjectName(constants.WIDGET_HELP_TAB)
        widgets.update(help_widgets)
        widgets[constants.WIDGET_HELP_TAB] = help_tab
        tabs.addTab(help_tab, "Help")

        return central_widget, widgets

    @staticmethod
    def create_toolbox_tab() -> Tuple[QtWidgets.QWidget, Dict[str, QtWidgets.QWidget]]:
        return create_toolbox_tab_layout()
