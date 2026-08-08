#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared toolbox tab context model used by the main window modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from PySide6 import QtWidgets

from app.canvas.toolbox_canvas import ToolboxCanvas
from app.domain.models import ToolboxEntry


@dataclass
class ToolboxTabContext:
    page: QtWidgets.QWidget
    splitter: QtWidgets.QSplitter
    drop_zone: QtWidgets.QWidget
    search_input: QtWidgets.QLineEdit
    canvas: ToolboxCanvas
    details_label: QtWidgets.QLabel
    add_tool_button: QtWidgets.QPushButton
    add_section_button: QtWidgets.QPushButton
    launch_button: QtWidgets.QPushButton
    remove_button: QtWidgets.QPushButton
    open_config_button: QtWidgets.QPushButton
    entries: list[ToolboxEntry]
    title: str
    tab_id: str
    is_primary: bool
    background_color: str
    selected_ids: set[str]
    # Browse state (not persisted)
    browse_stack: list[Path] = field(default_factory=list)  # stack of visited paths
    breadcrumb_bar: Optional[QtWidgets.QWidget] = field(default=None)  # injected after construction
    _browse_display_entries: list[ToolboxEntry] = field(default_factory=list)
