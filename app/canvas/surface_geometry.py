#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canvas surface geometry and section/tool conflict helpers."""

from __future__ import annotations

from PySide6 import QtCore

from app import constants
from app.canvas.section_conflicts import (
    nearest_non_conflicting_section_y,
    push_tools_below_section,
    resolve_section_protection_conflicts,
    section_drop_intersects_tools,
)
from app.domain.models import ToolboxEntry
from app.ui.widgets.canvas_widgets import SectionWidget


class CanvasSurfaceGeometryMixin:
    def insert_tool_row(self, entries: list[ToolboxEntry], target_y: int, below: bool) -> int:
        self._entries = entries
        insertion_y, segment_start, segment_end = self._layout_engine.insertion_row_y(
            self._entries, target_y, below
        )
        row_height = self._layout_engine.tool_cell_size()[1]
        shifted = 0
        for entry in self._entries:
            if not entry.is_tool:
                continue
            if entry.y < segment_start:
                continue
            if segment_end is not None and entry.y > segment_end:
                continue
            if entry.y >= insertion_y:
                entry.y += row_height
                shifted += 1
        if shifted:
            self._apply_geometry(compact_tools=False)
        return shifted

    def _apply_section_geometry(self) -> None:
        sections = [entry for entry in self._entries if entry.is_section]
        sections.sort(key=lambda item: (item.y, item.title.lower()))
        used_rows: set[int] = set()
        for entry in sections:
            target_row = self._layout_engine.section_row_from_y(entry.y)
            offsets = [0]
            for delta in range(1, 256):
                offsets.extend((delta, -delta))
            chosen_row = target_row
            for offset in offsets:
                row = max(0, target_row + offset)
                if row not in used_rows:
                    chosen_row = row
                    break
            used_rows.add(chosen_row)
            entry.x = constants.CANVAS_PADDING
            entry.y = self._layout_engine.section_y_from_row(chosen_row)
            widget = self._widgets.get(entry.entry_id)
            if widget is not None:
                widget.setGeometry(
                    entry.x,
                    entry.y,
                    self._layout_engine.content_width(),
                    self._layout_engine.section_height(),
                )
                if isinstance(widget, SectionWidget):
                    widget.set_drop_hint(False)
                widget.setVisible(entry.entry_id not in self._hidden_entry_ids)

    def _apply_tool_geometry(self, compact_rows: bool = False) -> None:
        tools = [entry for entry in self._entries if entry.is_tool]
        tools.sort(key=lambda item: (item.y, item.x, item.title.lower()))
        if compact_rows:
            occupied_rects: list[QtCore.QRect] = []
            section_bands = self._layout_engine.section_bands(self._entries)
            for entry in tools:
                # Compact each row from the left so gaps are automatically closed.
                target_col = 0
                entry.x, entry.y = self._layout_engine.find_nearest_free_cell(
                    target_col,
                    entry.y,
                    occupied_rects,
                    section_bands,
                )
                occupied_rects.append(self._layout_engine.tool_rect_at(entry.x, entry.y))

        for entry in tools:
            widget = self._widgets.get(entry.entry_id)
            if widget is not None:
                widget.move(entry.x, entry.y)
                widget.lower()
                widget.setVisible(entry.entry_id not in self._hidden_entry_ids)

    def compact_tools(self, entries: list[ToolboxEntry]) -> None:
        self._entries = entries
        self._apply_geometry(compact_tools=True)

    def _apply_geometry(self, compact_tools: bool = False) -> None:
        self._apply_section_geometry()
        self._apply_tool_geometry(compact_rows=compact_tools)
        for entry in self._entries:
            widget = self._widgets.get(entry.entry_id)
            if entry.is_section and widget is not None:
                widget.raise_()
        self._update_canvas_size()

    def _insert_tool_row_at_y(
        self, insertion_y: int, exclude_entry_id: str | None = None
    ) -> int:
        row_height = self._layout_engine.tool_cell_size()[1]
        shifted = 0
        for item in self._entries:
            if item.entry_id == exclude_entry_id:
                continue
            if item.y >= insertion_y:
                item.y += row_height
                shifted += 1
        return shifted

    def _section_drop_intersects_tools(
        self, section_y: int, exclude_entry_id: str | None = None
    ) -> bool:
        return section_drop_intersects_tools(
            self._entries,
            self._layout_engine,
            section_y,
            exclude_entry_id=exclude_entry_id,
        )

    def _nearest_non_conflicting_section_y(
        self, section_y: int, exclude_entry_id: str | None = None
    ) -> int:
        return nearest_non_conflicting_section_y(
            self._entries,
            self._layout_engine,
            section_y,
            exclude_entry_id=exclude_entry_id,
        )

    def _push_tools_below_section(
        self,
        section_y: int,
        excluded_entry_ids: set[str] | None = None,
    ) -> bool:
        return push_tools_below_section(
            self._entries,
            self._layout_engine,
            section_y,
            excluded_entry_ids=excluded_entry_ids,
        )

    def _resolve_section_protection_conflicts(self) -> bool:
        return resolve_section_protection_conflicts(self._entries, self._layout_engine)

    def _update_canvas_size(self) -> None:
        max_right = self._layout_engine.content_width() + (2 * constants.CANVAS_PADDING)
        max_bottom = 420
        for widget in self._widgets.values():
            if not widget.isVisible():
                continue
            max_right = max(max_right, widget.geometry().right() + constants.CANVAS_PADDING)
            max_bottom = max(max_bottom, widget.geometry().bottom() + constants.CANVAS_PADDING)
        self.resize(max_right, max_bottom)
        self.update()
