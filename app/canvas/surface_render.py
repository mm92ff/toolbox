#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canvas surface entry/widget rendering and style updates."""

from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from app import constants
from app.canvas.section_conflicts import (
    segment_index_for_y_in_ranges,
    shift_tools_for_segment_start_delta,
)
from app.domain.models import ToolboxEntry
from app.services.image_thumbnails import is_supported_image_path, load_or_create_thumbnail
from app.services.video_thumbnails import (
    is_supported_video_path,
    load_or_create_video_thumbnail,
)
from app.ui.widgets.canvas_widgets import CanvasItemBase, SectionWidget, ToolTileWidget


class CanvasSurfaceRenderMixin:
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
        viewport_width: int,
        section_gap_above: int | None = None,
        section_gap_below: int | None = None,
        image_file_preview_enabled: bool = constants.DEFAULT_IMAGE_FILE_PREVIEW_ENABLED,
        image_file_preview_mode: str = constants.DEFAULT_IMAGE_FILE_PREVIEW_MODE,
        video_file_preview_enabled: bool = constants.DEFAULT_VIDEO_FILE_PREVIEW_ENABLED,
        hover_preview_enabled: bool = constants.DEFAULT_HOVER_PREVIEW_ENABLED,
        ffmpeg_manual_path: str = "",
        thumbnail_cache_dir: Path | None = None,
    ) -> None:
        self.clear()
        self._entries = entries
        self._icon_provider = icon_provider
        self._auto_compact_left = auto_compact_left
        self._image_file_preview_enabled = image_file_preview_enabled
        self._image_file_preview_mode = image_file_preview_mode
        self._video_file_preview_enabled = video_file_preview_enabled
        self._hover_preview_enabled = hover_preview_enabled
        self._ffmpeg_manual_path = (ffmpeg_manual_path or "").strip()
        self._thumbnail_cache_dir = thumbnail_cache_dir
        self._selected_entry_ids = set(selected_entry_ids)
        self._hidden_entry_ids = set(hidden_entry_ids)

        self._layout_engine.set_viewport_width(viewport_width)
        self._layout_engine.configure(
            icon_size,
            grid_spacing_x,
            grid_spacing_y,
            section_font_size,
            section_line_thickness,
            section_gap,
            section_line_color,
            section_gap_above=section_gap_above,
            section_gap_below=section_gap_below,
        )

        for entry in self._entries:
            widget = self._create_widget(
                entry,
                tile_frame_enabled=tile_frame_enabled,
                tile_frame_thickness=tile_frame_thickness,
                tile_frame_color=tile_frame_color,
                tile_highlight_color=tile_highlight_color,
            )
            widget.setVisible(entry.entry_id not in self._hidden_entry_ids)
            self._widgets[entry.entry_id] = widget
            widget.show()

        self._resolve_section_protection_conflicts()
        self._apply_geometry(compact_tools=False)
        if self._resolve_tool_overlap_conflicts():
            self._apply_geometry(compact_tools=False)
        self._apply_selection()

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
        thumbnail_cache_dir: Path | None = None,
    ) -> bool:
        self._entries = entries
        self._auto_compact_left = auto_compact_left
        self._image_file_preview_enabled = image_file_preview_enabled
        self._image_file_preview_mode = image_file_preview_mode
        self._video_file_preview_enabled = video_file_preview_enabled
        self._hover_preview_enabled = hover_preview_enabled
        self._ffmpeg_manual_path = (ffmpeg_manual_path or "").strip()
        self._thumbnail_cache_dir = thumbnail_cache_dir
        previous_tool_cell_size = self._layout_engine.tool_cell_size()
        previous_segments = self._layout_engine.segment_ranges(self._entries)
        previous_tool_positions = {
            entry.entry_id: (entry.x, entry.y) for entry in self._entries if entry.is_tool
        }
        self._layout_engine.configure(
            icon_size,
            grid_spacing_x,
            grid_spacing_y,
            section_font_size,
            section_line_thickness,
            section_gap,
            section_line_color,
            section_gap_above=section_gap_above,
            section_gap_below=section_gap_below,
        )

        for widget in self._widgets.values():
            if isinstance(widget, ToolTileWidget):
                widget.set_icon(self._icon_for_tool_entry(widget.entry))
                widget.set_icon_size(self._layout_engine.icon_size)
                widget.set_tile_style(
                    frame_enabled=tile_frame_enabled,
                    frame_thickness=tile_frame_thickness,
                    frame_color=tile_frame_color,
                    highlight_color=tile_highlight_color,
                )
            elif isinstance(widget, SectionWidget):
                section_entry = next(
                    (
                        item
                        for item in self._entries
                        if item.entry_id == widget.entry.entry_id and item.is_section
                    ),
                    None,
                )
                if section_entry is None:
                    continue
                widget.set_section_style(
                    self._layout_engine.section_font_size,
                    self._layout_engine.section_line_thickness,
                    self._section_line_color_for_entry(section_entry),
                    self._section_title_color_for_entry(section_entry),
                )
        updated_segments = self._layout_engine.segment_ranges(self._entries)
        shifted_for_section_gap = shift_tools_for_segment_start_delta(
            self._entries,
            previous_segments,
            updated_segments,
        )
        remapped_for_tool_cell_size = self._remap_tools_for_cell_size_change(
            previous_tool_cell_size,
            self._layout_engine.tool_cell_size(),
            previous_segments,
            updated_segments,
            previous_tool_positions,
        )
        had_section_conflicts = self._resolve_section_protection_conflicts()
        self._apply_geometry(compact_tools=False)
        had_tool_overlap_conflicts = self._resolve_tool_overlap_conflicts()
        if had_tool_overlap_conflicts:
            self._apply_geometry(compact_tools=False)
        self._apply_selection()
        return (
            shifted_for_section_gap
            or remapped_for_tool_cell_size
            or had_section_conflicts
            or had_tool_overlap_conflicts
        )

    def _create_widget(
        self,
        entry: ToolboxEntry,
        tile_frame_enabled: bool,
        tile_frame_thickness: int,
        tile_frame_color: str,
        tile_highlight_color: str,
    ) -> CanvasItemBase:
        if entry.is_section:
            widget: CanvasItemBase = SectionWidget(
                entry,
                self._layout_engine.section_font_size,
                self._layout_engine.section_line_thickness,
                self._section_line_color_for_entry(entry),
                self._section_title_color_for_entry(entry),
                self,
            )
        else:
            icon = self._icon_for_tool_entry(entry)
            widget = ToolTileWidget(entry, icon, self._layout_engine.icon_size, self)
            widget.set_tile_style(
                frame_enabled=tile_frame_enabled,
                frame_thickness=tile_frame_thickness,
                frame_color=tile_frame_color,
                highlight_color=tile_highlight_color,
            )

        widget.clicked.connect(self.entry_clicked.emit)
        widget.double_clicked.connect(self.entry_activated.emit)
        widget.context_requested.connect(self.entry_context_requested.emit)
        widget.move_finished.connect(self._on_widget_move_finished)
        widget.move_live.connect(self._update_canvas_size)
        widget.move_live.connect(
            lambda entry_id=entry.entry_id: self._on_widget_move_live(entry_id)
        )
        if isinstance(widget, SectionWidget):
            widget.move_live.connect(
                lambda entry_id=entry.entry_id: self._on_section_move_live(entry_id)
            )
        if isinstance(widget, ToolTileWidget):
            widget.hover_started.connect(self.entry_hover_started.emit)
            widget.hover_ended.connect(self.entry_hover_ended.emit)
        return widget

    def _icon_for_tool_entry(self, entry: ToolboxEntry) -> QtGui.QIcon:
        if self._image_file_preview_enabled and is_supported_image_path(entry.path):
            pixmap = load_or_create_thumbnail(
                entry.path,
                self._layout_engine.icon_size,
                self._image_file_preview_mode,
                self._thumbnail_cache_dir,
                manual_ffmpeg_path=self._ffmpeg_manual_path,
            )
            if pixmap is not None and not pixmap.isNull():
                return QtGui.QIcon(pixmap)
        if self._video_file_preview_enabled and is_supported_video_path(entry.path):
            pixmap = load_or_create_video_thumbnail(
                entry.path,
                self._layout_engine.icon_size,
                self._image_file_preview_mode,
                self._thumbnail_cache_dir,
            )
            if pixmap is not None and not pixmap.isNull():
                return QtGui.QIcon(pixmap)

        icon = self._icon_provider.icon(QtCore.QFileInfo(entry.path))
        if icon.isNull():
            icon = self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DesktopIcon)
        return icon

    def _section_line_color_for_entry(self, entry: ToolboxEntry) -> str:
        custom_color = (entry.section_line_color or "").strip()
        if custom_color:
            return custom_color
        return self._layout_engine.section_line_color

    def hover_preview_pixmap_for_entry(
        self, entry_id: str, preview_size: int = constants.HOVER_PREVIEW_SIZE
    ) -> QtGui.QPixmap | None:
        if not self._hover_preview_enabled:
            return None
        entry = next((item for item in self._entries if item.entry_id == entry_id), None)
        if entry is None or not entry.is_tool:
            return None

        size = max(1, int(preview_size))
        if self._image_file_preview_enabled and is_supported_image_path(entry.path):
            return load_or_create_thumbnail(
                entry.path,
                size,
                self._image_file_preview_mode,
                self._thumbnail_cache_dir,
                manual_ffmpeg_path=self._ffmpeg_manual_path,
            )
        if self._video_file_preview_enabled and is_supported_video_path(entry.path):
            return load_or_create_video_thumbnail(
                entry.path,
                size,
                self._image_file_preview_mode,
                self._thumbnail_cache_dir,
            )
        return None

    @staticmethod
    def _section_title_color_for_entry(entry: ToolboxEntry) -> str:
        return (entry.section_title_color or "").strip()

    def _remap_tools_for_cell_size_change(
        self,
        previous_tool_cell_size: tuple[int, int],
        current_tool_cell_size: tuple[int, int],
        previous_segments: list[tuple[int, int | None]],
        updated_segments: list[tuple[int, int | None]],
        previous_tool_positions: dict[str, tuple[int, int]],
    ) -> bool:
        previous_cell_w, previous_cell_h = previous_tool_cell_size
        current_cell_w, current_cell_h = current_tool_cell_size
        if (
            previous_cell_w <= 0
            or previous_cell_h <= 0
            or previous_tool_cell_size == current_tool_cell_size
        ):
            return False
        if not previous_segments or not updated_segments:
            return False

        remapped = False
        for entry in self._entries:
            if not entry.is_tool:
                continue
            original_x, original_y = previous_tool_positions.get(entry.entry_id, (entry.x, entry.y))
            segment_index = segment_index_for_y_in_ranges(original_y, previous_segments)
            segment_index = max(0, min(segment_index, len(updated_segments) - 1))
            previous_segment_start, _ = previous_segments[segment_index]
            updated_segment_start, _ = updated_segments[segment_index]
            col = max(
                0,
                round((original_x - constants.CANVAS_PADDING) / max(1, previous_cell_w)),
            )
            row = max(
                0,
                round((original_y - previous_segment_start) / max(1, previous_cell_h)),
            )
            mapped_x = constants.CANVAS_PADDING + (col * current_cell_w)
            mapped_y = updated_segment_start + (row * current_cell_h)
            if mapped_x == entry.x and mapped_y == entry.y:
                continue
            entry.x = mapped_x
            entry.y = mapped_y
            remapped = True
        return remapped

    def _apply_selection(self) -> None:
        for entry_id, widget in self._widgets.items():
            widget.set_selected(entry_id in self._selected_entry_ids)
