#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canvas surface base state and lightweight accessors."""

from __future__ import annotations

from collections.abc import Iterable

from PySide6 import QtCore, QtWidgets

from app import constants
from app.canvas.layout_engine import CanvasLayoutEngine
from app.domain.models import ToolboxEntry
from app.ui.widgets.canvas_widgets import CanvasItemBase


class CanvasSurfaceStateMixin:
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._entries: list[ToolboxEntry] = []
        self._widgets: dict[str, CanvasItemBase] = {}
        self._icon_provider = QtWidgets.QFileIconProvider()
        self._layout_engine = CanvasLayoutEngine()
        self._auto_compact_left = constants.DEFAULT_AUTO_COMPACT_LEFT
        self._selected_entry_ids: set[str] = set()
        self._hidden_entry_ids: set[str] = set()
        self._selection_band = QtWidgets.QRubberBand(QtWidgets.QRubberBand.Shape.Rectangle, self)
        self._selection_origin = QtCore.QPoint()
        self._selection_active = False
        self._selection_additive = False
        self._selection_dragged = False
        self.setMinimumSize(900, 540)

    def clear(self) -> None:
        for widget in self._widgets.values():
            widget.deleteLater()
        self._widgets.clear()

    def set_viewport_width(self, viewport_width: int) -> None:
        self._layout_engine.set_viewport_width(viewport_width)
        self._apply_geometry(compact_tools=False)

    def select_entries(self, entry_ids: set[str]) -> None:
        self._selected_entry_ids = set(entry_ids)
        self._apply_selection()

    def selected_entry_ids(self) -> set[str]:
        return set(self._selected_entry_ids)

    def tool_tile_size(self) -> QtCore.QSize:
        return self._layout_engine.tool_tile_size()

    def section_height(self) -> int:
        return self._layout_engine.section_height()

    def minimum_tool_viewport_width(self) -> int:
        tile_width = self._layout_engine.tool_tile_size().width()
        max_right = 0
        for entry in self._entries:
            if not entry.is_tool:
                continue
            max_right = max(max_right, entry.x + tile_width)
        if max_right <= 0:
            return 480
        return max_right + constants.CANVAS_PADDING

    def find_next_free_tool_position(
        self, entries: Iterable[ToolboxEntry] | None = None
    ) -> tuple[int, int]:
        source_entries = list(entries) if entries is not None else list(self._entries)
        return self._layout_engine.find_next_free_tool_position(source_entries)

    def find_next_section_y(self, entries: Iterable[ToolboxEntry] | None = None) -> int:
        source_entries = list(entries) if entries is not None else list(self._entries)
        return self._layout_engine.find_next_section_y(source_entries)

    def snap_section_y(self, entries: Iterable[ToolboxEntry] | None, y: int) -> int:
        source_entries = list(entries) if entries is not None else list(self._entries)
        return self._layout_engine.snap_section_position(source_entries, y)
