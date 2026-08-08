#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canvas surface entry/widget rendering and style updates."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from app import constants
from app.canvas.section_conflicts import (
    segment_index_for_y_in_ranges,
    shift_tools_for_segment_start_delta,
)
from app.domain.models import ToolboxEntry
from app.services.image_thumbnails import is_supported_image_path, load_or_create_thumbnail
from app.services.linux_icon_theme import desktop_icon_for_path
from app.services.media_thumbnails import MEDIA_KIND_IMAGE, MEDIA_KIND_VIDEO
from app.services.thumbnail_cache import pixmap_for_requested_size, thumbnail_bucket_size
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
        preview_overlay_enabled: bool = constants.DEFAULT_PREVIEW_OVERLAY_ENABLED,
        video_file_preview_enabled: bool = constants.DEFAULT_VIDEO_FILE_PREVIEW_ENABLED,
        hover_preview_enabled: bool = constants.DEFAULT_HOVER_PREVIEW_ENABLED,
        ffmpeg_manual_path: str = "",
        thumbnail_cache_dir: Path | None = None,
        folder_show_file_count: bool = constants.DEFAULT_FOLDER_SHOW_FILE_COUNT,
        show_tooltips: bool = constants.DEFAULT_SHOW_TOOLTIPS,
        tile_font_size: int | None = None,
        responsive_layout: bool = False,
    ) -> None:
        self.clear()
        self._entries = entries
        self._icon_provider = icon_provider
        self._auto_compact_left = auto_compact_left
        self._image_file_preview_enabled = image_file_preview_enabled
        self._image_file_preview_mode = image_file_preview_mode
        self._preview_overlay_enabled = preview_overlay_enabled
        self._video_file_preview_enabled = video_file_preview_enabled
        self._hover_preview_enabled = hover_preview_enabled
        self._ffmpeg_manual_path = (ffmpeg_manual_path or "").strip()
        self._thumbnail_cache_dir = thumbnail_cache_dir
        self._folder_show_file_count = folder_show_file_count
        self._show_tooltips = show_tooltips
        self._selected_entry_ids = set(selected_entry_ids)
        self._hidden_entry_ids = set(hidden_entry_ids)
        self._responsive_layout_enabled = bool(responsive_layout)

        self._layout_engine.set_viewport_width(viewport_width)
        self._layout_engine.configure(
            icon_size,
            grid_spacing_x,
            grid_spacing_y,
            section_font_size,
            section_line_thickness,
            section_gap,
            section_line_color,
            tile_font_size=tile_font_size,
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
            widget.set_movement_enabled(not self._responsive_layout_enabled)
            self._widgets[entry.entry_id] = widget
            widget.show()

        if not self._responsive_layout_enabled:
            self._resolve_section_protection_conflicts()
        self._apply_geometry(compact_tools=False)
        if not self._responsive_layout_enabled and self._resolve_tool_overlap_conflicts():
            self._apply_geometry(compact_tools=False)
        self._apply_selection()
        for widget in self._widgets.values():
            if isinstance(widget, ToolTileWidget):
                self._refresh_tool_icon(widget, defer_generation=False)

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
        preview_overlay_enabled: bool = constants.DEFAULT_PREVIEW_OVERLAY_ENABLED,
        video_file_preview_enabled: bool = constants.DEFAULT_VIDEO_FILE_PREVIEW_ENABLED,
        hover_preview_enabled: bool = constants.DEFAULT_HOVER_PREVIEW_ENABLED,
        ffmpeg_manual_path: str = "",
        thumbnail_cache_dir: Path | None = None,
        folder_show_file_count: bool = constants.DEFAULT_FOLDER_SHOW_FILE_COUNT,
        show_tooltips: bool = constants.DEFAULT_SHOW_TOOLTIPS,
        tile_font_size: int | None = None,
        responsive_layout: bool = False,
    ) -> bool:
        self._entries = entries
        self._auto_compact_left = auto_compact_left
        self._image_file_preview_enabled = image_file_preview_enabled
        self._image_file_preview_mode = image_file_preview_mode
        self._preview_overlay_enabled = preview_overlay_enabled
        self._video_file_preview_enabled = video_file_preview_enabled
        self._hover_preview_enabled = hover_preview_enabled
        self._show_tooltips = show_tooltips
        self._ffmpeg_manual_path = (ffmpeg_manual_path or "").strip()
        self._thumbnail_cache_dir = thumbnail_cache_dir
        self._folder_show_file_count = folder_show_file_count
        self._responsive_layout_enabled = bool(responsive_layout)
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
            tile_font_size=tile_font_size,
            section_gap_above=section_gap_above,
            section_gap_below=section_gap_below,
        )

        for widget in self._widgets.values():
            widget.set_movement_enabled(not self._responsive_layout_enabled)
            if isinstance(widget, ToolTileWidget):
                is_media = (self._image_file_preview_enabled and is_supported_image_path(widget.entry.path)) or \
                           (self._video_file_preview_enabled and is_supported_video_path(widget.entry.path))
                widget.set_overlay_mode(self._preview_overlay_enabled and is_media)
                widget.set_folder_file_count_mode(self._folder_show_file_count)
                widget.set_icon_size(
                    self._layout_engine.icon_size,
                    self._layout_engine.tile_font_size,
                )
                # Existing media is scaled immediately. Expensive regeneration is
                # delayed and performed by MediaThumbnailService off the GUI thread.
                self._refresh_tool_icon(widget, defer_generation=True)
                widget.set_show_tooltips(self._show_tooltips)
                widget.set_tile_style(
                    frame_enabled=tile_frame_enabled,
                    frame_thickness=tile_frame_thickness,
                    frame_color=tile_frame_color,
                    highlight_color=tile_highlight_color,
                )
            elif isinstance(widget, SectionWidget):
                widget.set_show_tooltips(self._show_tooltips)
                widget.set_section_style(
                    self._layout_engine.section_font_size,
                    self._layout_engine.section_line_thickness,
                    self._section_line_color_for_entry(widget.entry),
                    self._section_title_color_for_entry(widget.entry),
                )
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
        if self._responsive_layout_enabled:
            self._apply_geometry(compact_tools=False)
            self._apply_selection()
            return False

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
            is_media = (self._image_file_preview_enabled and is_supported_image_path(entry.path)) or \
                       (self._video_file_preview_enabled and is_supported_video_path(entry.path))
            
            icon = self._icon_for_tool_entry(entry)
            widget = ToolTileWidget(
                entry,
                icon,
                self._layout_engine.icon_size,
                self,
                folder_count_service=self._folder_count_service,
                tile_font_size=self._layout_engine.tile_font_size,
            )
            widget.set_overlay_mode(self._preview_overlay_enabled and is_media)
            widget.set_icon(icon)
            widget.set_folder_file_count_mode(self._folder_show_file_count)
            widget.set_icon_size(
                self._layout_engine.icon_size,
                self._layout_engine.tile_font_size,
            )
            widget.set_show_tooltips(self._show_tooltips)
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
        widget.movement_blocked.connect(self.responsive_move_blocked.emit)
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
            widget.files_dropped.connect(self.entry_files_dropped.emit)
        return widget

    def _icon_for_tool_entry(self, entry: ToolboxEntry) -> QtGui.QIcon:
        if entry.custom_icon_path:
            pixmap = QtGui.QPixmap(entry.custom_icon_path)
            if not pixmap.isNull():
                return QtGui.QIcon(pixmap)

        cached_icon = self._cached_media_icon(entry)
        if cached_icon is not None:
            return cached_icon

        fallback = self.style().standardIcon(
            QtWidgets.QStyle.StandardPixmap.SP_DesktopIcon
        )
        return desktop_icon_for_path(
            entry.path,
            self._icon_provider,
            fallback,
            self._appimage_icon_service,
        )

    def _media_kind_for_entry(self, entry: ToolboxEntry) -> str | None:
        if entry.custom_icon_path:
            return None
        if self._image_file_preview_enabled and is_supported_image_path(entry.path):
            return MEDIA_KIND_IMAGE
        if self._video_file_preview_enabled and is_supported_video_path(entry.path):
            return MEDIA_KIND_VIDEO
        return None

    def _media_target_size(self, entry: ToolboxEntry) -> int:
        is_media = self._media_kind_for_entry(entry) is not None
        if self._preview_overlay_enabled and is_media:
            return self._layout_engine.tool_tile_size().width()
        return self._layout_engine.icon_size

    def _cached_media_icon(self, entry: ToolboxEntry) -> QtGui.QIcon | None:
        kind = self._media_kind_for_entry(entry)
        if kind is None:
            return None
        target_size = self._media_target_size(entry)
        cache_path = self._media_thumbnail_service.cached_path(
            entry.path,
            kind,
            target_size,
            self._image_file_preview_mode,
            self._thumbnail_cache_dir,
        )
        if cache_path is None:
            return None
        pixmap = pixmap_for_requested_size(cache_path, target_size)
        return None if pixmap.isNull() else QtGui.QIcon(pixmap)

    def _refresh_tool_icon(
        self,
        widget: ToolTileWidget,
        *,
        defer_generation: bool,
    ) -> None:
        entry = widget.entry
        kind = self._media_kind_for_entry(entry)
        if kind is None:
            widget.set_icon(self._icon_for_tool_entry(entry))
            self._pending_media_entry_ids.discard(entry.entry_id)
            return

        cached_icon = self._cached_media_icon(entry)
        if cached_icon is not None:
            widget.set_icon(cached_icon)
            self._pending_media_entry_ids.discard(entry.entry_id)
            return

        self._pending_media_entry_ids.add(entry.entry_id)
        if defer_generation:
            self._media_request_timer.start()
        else:
            self._request_pending_media_thumbnails()

    @QtCore.Slot()
    def _request_pending_media_thumbnails(self) -> None:
        self._media_request_timer.stop()
        pending_ids = tuple(self._pending_media_entry_ids)
        self._pending_media_entry_ids.clear()
        widgets: list[ToolTileWidget] = []
        for entry_id in pending_ids:
            widget = self._widgets.get(entry_id)
            if isinstance(widget, ToolTileWidget) and not widget.isHidden():
                widgets.append(widget)
        widgets.sort(key=lambda item: item.visibleRegion().isEmpty())
        for widget in widgets:
            entry = widget.entry
            kind = self._media_kind_for_entry(entry)
            if kind is None:
                continue
            request_kwargs: dict[str, object] = {
                "priority": 1 if not widget.visibleRegion().isEmpty() else 0,
            }
            if kind == MEDIA_KIND_VIDEO:
                request_kwargs["manual_ffmpeg_path"] = self._ffmpeg_manual_path
            self._media_thumbnail_service.request(
                entry.path,
                kind,
                self._media_target_size(entry),
                self._image_file_preview_mode,
                self._thumbnail_cache_dir,
                **request_kwargs,
            )

    @QtCore.Slot(str, str, int, str, str)
    def _on_media_thumbnail_ready(
        self,
        path: str,
        kind: str,
        bucket_size: int,
        mode: str,
        thumbnail_path: str,
    ) -> None:
        normalized = os.path.abspath(os.path.expanduser(path))
        for entry in self._entries:
            if not entry.is_tool or self._media_kind_for_entry(entry) != kind:
                continue
            if os.path.abspath(os.path.expanduser(entry.path)) != normalized:
                continue
            target_size = self._media_target_size(entry)
            if thumbnail_bucket_size(target_size) != bucket_size:
                continue
            if (self._image_file_preview_mode or "").strip().lower() != mode:
                continue
            widget = self._widgets.get(entry.entry_id)
            if not isinstance(widget, ToolTileWidget):
                continue
            pixmap = pixmap_for_requested_size(thumbnail_path, target_size)
            if not pixmap.isNull():
                widget.set_icon(QtGui.QIcon(pixmap))

    @QtCore.Slot(str, str)
    def _on_appimage_icon_ready(self, path: str, icon_path: str) -> None:
        icon = QtGui.QIcon(icon_path)
        if icon.isNull():
            return
        normalized = os.path.abspath(os.path.expanduser(path))
        for entry in self._entries:
            if not entry.is_tool or entry.custom_icon_path:
                continue
            if os.path.abspath(os.path.expanduser(entry.path)) != normalized:
                continue
            widget = self._widgets.get(entry.entry_id)
            if isinstance(widget, ToolTileWidget):
                widget.set_icon(icon)

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
            )
        if self._video_file_preview_enabled and is_supported_video_path(entry.path):
            return load_or_create_video_thumbnail(
                entry.path,
                size,
                self._image_file_preview_mode,
                self._thumbnail_cache_dir,
                manual_ffmpeg_path=self._ffmpeg_manual_path,
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
