#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Movable toolbox canvas with long-press drag and snap-to-grid tiles."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from app import constants
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
    entry_hover_started = QtCore.Signal(str, QtCore.QPoint)
    entry_hover_ended = QtCore.Signal(str)


class ToolboxCanvas(QtWidgets.QScrollArea):
    entry_clicked = QtCore.Signal(str)
    background_clicked = QtCore.Signal()
    background_context_requested = QtCore.Signal(QtCore.QPoint, QtCore.QPoint)
    area_selection_finished = QtCore.Signal(object, bool)
    entry_activated = QtCore.Signal(str)
    entry_context_requested = QtCore.Signal(str, QtCore.QPoint)
    entry_moved = QtCore.Signal(str, int, int)
    entry_hover_started = QtCore.Signal(str, QtCore.QPoint)
    entry_hover_ended = QtCore.Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("toolbox_canvas_scroll")
        self.setWidgetResizable(False)
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignTop)
        self.surface = CanvasSurface(self)
        self.surface.setObjectName("toolbox_canvas_surface")
        self.viewport().setObjectName("toolbox_canvas_viewport")
        self.setWidget(self.surface)
        self._background_color = ""
        self._hover_preview_enabled = constants.DEFAULT_HOVER_PREVIEW_ENABLED
        self._hover_preview_popup: QtWidgets.QLabel | None = None
        self._hover_preview_entry_id: str | None = None
        self._thumbnail_cache_dir: Path | None = None
        self._default_viewport_palette = QtGui.QPalette(self.viewport().palette())
        self._default_surface_palette = QtGui.QPalette(self.surface.palette())
        self.surface.entry_clicked.connect(self.entry_clicked.emit)
        self.surface.background_clicked.connect(self.background_clicked.emit)
        self.surface.background_context_requested.connect(self.background_context_requested.emit)
        self.surface.area_selection_finished.connect(self.area_selection_finished.emit)
        self.surface.entry_activated.connect(self.entry_activated.emit)
        self.surface.entry_context_requested.connect(self.entry_context_requested.emit)
        self.surface.entry_moved.connect(self.entry_moved.emit)
        self.surface.entry_hover_started.connect(self._on_entry_hover_started)
        self.surface.entry_hover_ended.connect(self._on_entry_hover_ended)
        self.surface.entry_hover_started.connect(self.entry_hover_started.emit)
        self.surface.entry_hover_ended.connect(self.entry_hover_ended.emit)
        self.verticalScrollBar().valueChanged.connect(lambda _value: self._hide_hover_preview())
        self.horizontalScrollBar().valueChanged.connect(lambda _value: self._hide_hover_preview())

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
        image_file_preview_enabled: bool = constants.DEFAULT_IMAGE_FILE_PREVIEW_ENABLED,
        image_file_preview_mode: str = constants.DEFAULT_IMAGE_FILE_PREVIEW_MODE,
        video_file_preview_enabled: bool = constants.DEFAULT_VIDEO_FILE_PREVIEW_ENABLED,
        hover_preview_enabled: bool = constants.DEFAULT_HOVER_PREVIEW_ENABLED,
        ffmpeg_manual_path: str = "",
    ) -> None:
        self._hover_preview_enabled = bool(hover_preview_enabled)
        self._hide_hover_preview()
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
            image_file_preview_enabled=image_file_preview_enabled,
            image_file_preview_mode=image_file_preview_mode,
            video_file_preview_enabled=video_file_preview_enabled,
            hover_preview_enabled=self._hover_preview_enabled,
            ffmpeg_manual_path=ffmpeg_manual_path,
            thumbnail_cache_dir=self._thumbnail_cache_dir,
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
        image_file_preview_enabled: bool = constants.DEFAULT_IMAGE_FILE_PREVIEW_ENABLED,
        image_file_preview_mode: str = constants.DEFAULT_IMAGE_FILE_PREVIEW_MODE,
        video_file_preview_enabled: bool = constants.DEFAULT_VIDEO_FILE_PREVIEW_ENABLED,
        hover_preview_enabled: bool = constants.DEFAULT_HOVER_PREVIEW_ENABLED,
        ffmpeg_manual_path: str = "",
    ) -> bool:
        self._hover_preview_enabled = bool(hover_preview_enabled)
        self._hide_hover_preview()
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
            image_file_preview_enabled=image_file_preview_enabled,
            image_file_preview_mode=image_file_preview_mode,
            video_file_preview_enabled=video_file_preview_enabled,
            hover_preview_enabled=self._hover_preview_enabled,
            ffmpeg_manual_path=ffmpeg_manual_path,
            thumbnail_cache_dir=self._thumbnail_cache_dir,
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

    @staticmethod
    def _normalize_background_color(value: str) -> str:
        color = QtGui.QColor((value or "").strip())
        if not color.isValid():
            return ""
        return color.name()

    def set_background_color(self, color_value: str) -> None:
        normalized = self._normalize_background_color(color_value)
        self._background_color = normalized
        self.setStyleSheet("")
        self.viewport().setStyleSheet("")
        self.surface.setStyleSheet("")
        if not normalized:
            self.viewport().setPalette(QtGui.QPalette(self._default_viewport_palette))
            self.surface.setPalette(QtGui.QPalette(self._default_surface_palette))
            self.viewport().setAutoFillBackground(False)
            self.surface.setAutoFillBackground(False)
            self.viewport().setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, False)
            self.surface.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, False)
            self.viewport().update()
            self.surface.update()
            return

        color = QtGui.QColor(normalized)
        viewport_palette = QtGui.QPalette(self.viewport().palette())
        viewport_palette.setColor(QtGui.QPalette.ColorRole.Window, color)
        surface_palette = QtGui.QPalette(self.surface.palette())
        surface_palette.setColor(QtGui.QPalette.ColorRole.Window, color)
        self.viewport().setPalette(viewport_palette)
        self.surface.setPalette(surface_palette)
        self.viewport().setAutoFillBackground(True)
        self.surface.setAutoFillBackground(True)
        self.viewport().setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, False)
        self.surface.setAttribute(QtCore.Qt.WidgetAttribute.WA_StyledBackground, False)
        self.viewport().update()
        self.surface.update()

    def background_color(self) -> str:
        return self._background_color

    def set_thumbnail_cache_dir(self, cache_dir: Path | None) -> None:
        self._thumbnail_cache_dir = cache_dir

    def _ensure_hover_preview_popup(self) -> QtWidgets.QLabel:
        if self._hover_preview_popup is not None:
            return self._hover_preview_popup
        popup = QtWidgets.QLabel(None)
        popup.setObjectName("toolbox_hover_preview_popup")
        popup.setWindowFlags(
            QtCore.Qt.WindowType.ToolTip
            | QtCore.Qt.WindowType.FramelessWindowHint
            | QtCore.Qt.WindowType.WindowStaysOnTopHint
        )
        popup.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        popup.setStyleSheet(
            """
            QLabel#toolbox_hover_preview_popup {
                background: rgba(14, 18, 26, 228);
                border: 1px solid rgba(170, 188, 220, 160);
                border-radius: 8px;
                padding: 6px;
            }
            """
        )
        self._hover_preview_popup = popup
        return popup

    def _position_hover_preview_popup(
        self, popup: QtWidgets.QLabel, anchor_global: QtCore.QPoint
    ) -> None:
        pos = QtCore.QPoint(anchor_global.x() + 10, anchor_global.y() + 4)
        popup.adjustSize()
        geometry = popup.frameGeometry()
        screen = QtGui.QGuiApplication.screenAt(anchor_global) or QtGui.QGuiApplication.primaryScreen()
        if screen is None:
            popup.move(pos)
            return
        available = screen.availableGeometry()
        if geometry.width() > available.width():
            geometry.setWidth(available.width())
        if geometry.height() > available.height():
            geometry.setHeight(available.height())
        if pos.x() + geometry.width() > available.right():
            pos.setX(max(available.left(), anchor_global.x() - geometry.width() - 10))
        if pos.y() + geometry.height() > available.bottom():
            pos.setY(max(available.top(), available.bottom() - geometry.height()))
        popup.move(pos)

    def _show_hover_preview(self, entry_id: str, anchor_global: QtCore.QPoint) -> None:
        if not self._hover_preview_enabled:
            self._hide_hover_preview()
            return
        pixmap = self.surface.hover_preview_pixmap_for_entry(
            entry_id, preview_size=constants.HOVER_PREVIEW_SIZE
        )
        if pixmap is None or pixmap.isNull():
            self._hide_hover_preview()
            return
        popup = self._ensure_hover_preview_popup()
        popup.setPixmap(pixmap)
        self._position_hover_preview_popup(popup, anchor_global)
        popup.show()
        popup.raise_()
        self._hover_preview_entry_id = entry_id

    def _hide_hover_preview(self) -> None:
        self._hover_preview_entry_id = None
        if self._hover_preview_popup is not None:
            self._hover_preview_popup.hide()

    def _on_entry_hover_started(self, entry_id: str, anchor_global: QtCore.QPoint) -> None:
        self._show_hover_preview(entry_id, anchor_global)

    def _on_entry_hover_ended(self, _entry_id: str) -> None:
        self._hide_hover_preview()

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        super().resizeEvent(event)
        self._hide_hover_preview()
        self.surface.set_viewport_width(self.viewport().width())
