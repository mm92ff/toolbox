#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canvas surface entry/widget rendering and style updates."""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from app.canvas.section_conflicts import shift_tools_for_segment_start_delta
from app.domain.models import ToolboxEntry
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
    ) -> None:
        self.clear()
        self._entries = entries
        self._icon_provider = icon_provider
        self._auto_compact_left = auto_compact_left
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
    ) -> bool:
        self._entries = entries
        self._auto_compact_left = auto_compact_left
        previous_segments = self._layout_engine.segment_ranges(self._entries)
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
        had_conflicts = self._resolve_section_protection_conflicts()
        self._apply_geometry(compact_tools=False)
        self._apply_selection()
        return shifted_for_section_gap or had_conflicts

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
            icon = self._icon_provider.icon(QtCore.QFileInfo(entry.path))
            if icon.isNull():
                icon = self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DesktopIcon)
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
        return widget

    def _section_line_color_for_entry(self, entry: ToolboxEntry) -> str:
        custom_color = (entry.section_line_color or "").strip()
        if custom_color:
            return custom_color
        return self._layout_engine.section_line_color

    @staticmethod
    def _section_title_color_for_entry(entry: ToolboxEntry) -> str:
        return (entry.section_title_color or "").strip()

    def _apply_selection(self) -> None:
        for entry_id, widget in self._widgets.items():
            widget.set_selected(entry_id in self._selected_entry_ids)
