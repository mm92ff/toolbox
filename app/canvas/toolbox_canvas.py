#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Movable toolbox canvas with long-press drag and snap-to-grid tiles."""

from __future__ import annotations

from collections.abc import Iterable

from PySide6 import QtCore, QtGui, QtWidgets

from app.canvas.surface_drag import CanvasSurfaceDragMixin
from app.canvas.surface_geometry import CanvasSurfaceGeometryMixin
from app.canvas.surface_interaction import CanvasSurfaceInteractionMixin
from app.canvas.surface_render import CanvasSurfaceRenderMixin
from app.canvas.surface_state import CanvasSurfaceStateMixin
from app.domain.models import ToolboxEntry


class CanvasSurface(
    CanvasSurfaceInteractionMixin,
    CanvasSurfaceDragMixin,
    CanvasSurfaceGeometryMixin,
    CanvasSurfaceRenderMixin,
    CanvasSurfaceStateMixin,
    QtWidgets.QWidget,
):
    entry_clicked = QtCore.Signal(str)
    background_clicked = QtCore.Signal()
    background_context_requested = QtCore.Signal(QtCore.QPoint, QtCore.QPoint)
    area_selection_finished = QtCore.Signal(object, bool)
    entry_activated = QtCore.Signal(str)
    entry_context_requested = QtCore.Signal(str, QtCore.QPoint)
    entry_moved = QtCore.Signal(str, int, int)


class ToolboxCanvas(QtWidgets.QScrollArea):
    entry_clicked = QtCore.Signal(str)
    background_clicked = QtCore.Signal()
    background_context_requested = QtCore.Signal(QtCore.QPoint, QtCore.QPoint)
    area_selection_finished = QtCore.Signal(object, bool)
    entry_activated = QtCore.Signal(str)
    entry_context_requested = QtCore.Signal(str, QtCore.QPoint)
    entry_moved = QtCore.Signal(str, int, int)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWidgetResizable(False)
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        self.surface = CanvasSurface(self)
        self.setWidget(self.surface)
        self.surface.entry_clicked.connect(self.entry_clicked.emit)
        self.surface.background_clicked.connect(self.background_clicked.emit)
        self.surface.background_context_requested.connect(self.background_context_requested.emit)
        self.surface.area_selection_finished.connect(self.area_selection_finished.emit)
        self.surface.entry_activated.connect(self.entry_activated.emit)
        self.surface.entry_context_requested.connect(self.entry_context_requested.emit)
        self.surface.entry_moved.connect(self.entry_moved.emit)

    def set_entries(
        self,
        entries: list[ToolboxEntry],
        icon_provider: QtWidgets.QFileIconProvider,
        icon_size: int,
        tile_frame_enabled: bool,
        tile_frame_thickness: int,
        tile_frame_color: str,
        tile_highlight_color: str,
        grid_spacing_x: int,
        grid_spacing_y: int,
        auto_compact_left: bool,
        section_font_size: int,
        section_line_thickness: int,
        section_gap: int,
        section_line_color: str,
        selected_entry_ids: set[str],
        hidden_entry_ids: set[str],
        section_gap_above: int | None = None,
        section_gap_below: int | None = None,
    ) -> None:
        self.surface.set_entries(
            entries,
            icon_provider,
            icon_size,
            tile_frame_enabled,
            tile_frame_thickness,
            tile_frame_color,
            tile_highlight_color,
            grid_spacing_x,
            grid_spacing_y,
            auto_compact_left,
            section_font_size,
            section_line_thickness,
            section_gap,
            section_line_color,
            selected_entry_ids,
            hidden_entry_ids,
            self.viewport().width(),
            section_gap_above=section_gap_above,
            section_gap_below=section_gap_below,
        )

    def apply_layout_settings(
        self,
        entries: list[ToolboxEntry],
        icon_size: int,
        tile_frame_enabled: bool,
        tile_frame_thickness: int,
        tile_frame_color: str,
        tile_highlight_color: str,
        grid_spacing_x: int,
        grid_spacing_y: int,
        auto_compact_left: bool,
        section_font_size: int,
        section_line_thickness: int,
        section_gap: int,
        section_line_color: str,
        section_gap_above: int | None = None,
        section_gap_below: int | None = None,
    ) -> bool:
        return self.surface.apply_layout_settings(
            entries,
            icon_size,
            tile_frame_enabled,
            tile_frame_thickness,
            tile_frame_color,
            tile_highlight_color,
            grid_spacing_x,
            grid_spacing_y,
            auto_compact_left,
            section_font_size,
            section_line_thickness,
            section_gap,
            section_line_color,
            section_gap_above=section_gap_above,
            section_gap_below=section_gap_below,
        )

    def select_entries(self, entry_ids: set[str]) -> None:
        self.surface.select_entries(entry_ids)

    def selected_entry_ids(self) -> set[str]:
        return self.surface.selected_entry_ids()

    def minimum_tool_viewport_width(self) -> int:
        return self.surface.minimum_tool_viewport_width()

    def find_next_free_tool_position(
        self, entries: Iterable[ToolboxEntry] | None = None
    ) -> tuple[int, int]:
        return self.surface.find_next_free_tool_position(entries)

    def find_next_section_y(self, entries: Iterable[ToolboxEntry] | None = None) -> int:
        return self.surface.find_next_section_y(entries)

    def snap_section_y(self, entries: Iterable[ToolboxEntry] | None, y: int) -> int:
        return self.surface.snap_section_y(entries, y)

    def insert_tool_row(self, entries: list[ToolboxEntry], target_y: int, below: bool) -> int:
        return self.surface.insert_tool_row(entries, target_y, below)

    def compact_tools(self, entries: list[ToolboxEntry]) -> None:
        self.surface.compact_tools(entries)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self.surface.set_viewport_width(self.viewport().width())
