#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canvas surface drag, drop, and move-finalization behavior."""

from __future__ import annotations

from bisect import bisect_right

from PySide6 import QtCore

from app import constants
from app.domain.models import ToolboxEntry
from app.ui.widgets.canvas_widgets import SectionWidget


class CanvasSurfaceDragMixin:
    def _on_section_move_live(self, entry_id: str) -> None:
        entry = next(
            (item for item in self._entries if item.entry_id == entry_id and item.is_section), None
        )
        widget = self._widgets.get(entry_id)
        if entry is None or widget is None or not isinstance(widget, SectionWidget):
            return

        is_group_move = len(self._selected_entry_ids) > 1 and entry_id in self._selected_entry_ids

        target_y = widget.y()
        snapped_y = self._layout_engine.snap_section_position(
            self._entries, target_y, exclude_entry_id=entry_id
        )
        would_push_tools = self._section_drop_intersects_tools(
            snapped_y, exclude_entry_id=entry_id
        )
        safe_y = self._nearest_non_conflicting_section_y(snapped_y, exclude_entry_id=entry_id)
        step = self._layout_engine.section_step()
        boundary_critical = self._section_drop_intersects_tools(
            max(constants.CANVAS_PADDING, safe_y - step), exclude_entry_id=entry_id
        )
        snap_threshold = max(10, self._layout_engine.section_step() // 4)
        near_boundary = abs(safe_y - target_y) <= snap_threshold or safe_y != snapped_y
        if near_boundary:
            display_y = safe_y
        else:
            display_y = target_y
        if would_push_tools:
            widget.set_drop_hint("conflict")
        elif near_boundary and boundary_critical:
            widget.set_drop_hint("snap")
        else:
            widget.set_drop_hint("none")
        if is_group_move:
            # For multi-select we only keep the hint active.
            # Repositioning during live drag causes visible jumps.
            return
        widget.setGeometry(
            constants.CANVAS_PADDING,
            display_y,
            self._layout_engine.content_width(),
            self._layout_engine.section_height(),
        )

    def _on_widget_move_finished(self, entry_id: str, x: int, y: int) -> None:
        entry = next((item for item in self._entries if item.entry_id == entry_id), None)
        widget = self._widgets.get(entry_id)
        if entry is None or widget is None:
            return

        if len(self._selected_entry_ids) > 1 and entry_id in self._selected_entry_ids:
            self._finalize_group_move(entry_id)
            return

        self._finalize_single_move(entry, x, y)

    def _finalize_single_move(
        self, entry: ToolboxEntry, x: int, y: int, emit_signal: bool = True
    ) -> None:
        widget = self._widgets.get(entry.entry_id)
        if widget is None:
            return

        if entry.is_tool:
            if not self._auto_compact_left:
                entry.x, entry.y = self._layout_engine.snap_tool_position(
                    self._entries,
                    x,
                    y,
                    exclude_entry_id=entry.entry_id,
                )
                widget.move(entry.x, entry.y)
                widget.lower()
                self._apply_geometry(compact_tools=False)
                self._update_canvas_size()
                if emit_signal:
                    self.entry_moved.emit(entry.entry_id, entry.x, entry.y)
                return

            drop_x = x
            drop_y = y
            if hasattr(widget, "last_release_parent_pos"):
                release_pos = widget.last_release_parent_pos()
                if release_pos != QtCore.QPoint(-1, -1):
                    drop_x = release_pos.x()
                    drop_y = release_pos.y()

            other_entries = [item for item in self._entries if item.entry_id != entry.entry_id]
            preferred_segment_index = self._layout_engine.segment_index_for_y(other_entries, drop_y)
            _, snapped_y = self._layout_engine.snap_tool_position(
                self._entries, drop_x, drop_y, exclude_entry_id=entry.entry_id
            )
            resolved_segment_index = self._layout_engine.segment_index_for_y(
                other_entries, snapped_y
            )

            if resolved_segment_index > preferred_segment_index:
                insertion_y, _, _ = self._layout_engine.insertion_row_y(
                    other_entries, drop_y, below=True
                )
                self._insert_tool_row_at_y(insertion_y, exclude_entry_id=entry.entry_id)
                other_entries = [item for item in self._entries if item.entry_id != entry.entry_id]

            insertion_y, _, _ = self._layout_engine.insertion_row_y(
                other_entries, drop_y, below=False
            )
            self._insert_tool_into_row(
                other_entries=other_entries,
                moving_entry=entry,
                row_y=insertion_y,
                drop_x=drop_x,
                drop_y=drop_y,
            )
            widget.move(entry.x, entry.y)
            widget.lower()
            self._apply_geometry(compact_tools=False)
        else:
            entry.x = constants.CANVAS_PADDING
            entry.y = self._layout_engine.snap_section_position(
                self._entries, y, exclude_entry_id=entry.entry_id
            )
            self._push_tools_below_section(entry.y)
            widget.setGeometry(
                entry.x,
                entry.y,
                self._layout_engine.content_width(),
                self._layout_engine.section_height(),
            )
            self._apply_geometry(compact_tools=False)
        self._update_canvas_size()
        if emit_signal:
            self.entry_moved.emit(entry.entry_id, entry.x, entry.y)

    def _insert_tool_into_row(
        self,
        other_entries: list[ToolboxEntry],
        moving_entry: ToolboxEntry,
        row_y: int,
        drop_x: int,
        drop_y: int,
    ) -> None:
        cell_w, cell_h = self._layout_engine.tool_cell_size()
        cell_w = max(1, cell_w)
        cell_h = max(1, cell_h)
        segments = self._layout_engine.segment_ranges(other_entries)
        target_segment_index = self._layout_engine.segment_index_for_y(other_entries, drop_y)
        if not segments:
            moving_entry.x = constants.CANVAS_PADDING
            moving_entry.y = row_y
            return

        target_segment_index = max(0, min(target_segment_index, len(segments) - 1))
        segment_start, _segment_end = segments[target_segment_index]
        target_row_index = max(0, round((row_y - segment_start) / cell_h))

        row_tools = []
        for item in other_entries:
            if not item.is_tool:
                continue
            item_segment_index = self._layout_engine.segment_index_for_y(other_entries, item.y)
            if item_segment_index != target_segment_index:
                continue
            item_row_index = max(0, round((item.y - segment_start) / cell_h))
            if item_row_index == target_row_index:
                row_tools.append(item)

        row_tools.sort(key=lambda item: (item.x, item.title.lower()))
        centers = [item.x + (cell_w // 2) for item in row_tools]
        insert_index = bisect_right(centers, drop_x)

        ordered_row = list(row_tools)
        ordered_row.insert(insert_index, moving_entry)

        for col_index, item in enumerate(ordered_row):
            item.x = constants.CANVAS_PADDING + (col_index * cell_w)
            item.y = row_y

    def _on_widget_move_live(self, entry_id: str) -> None:
        if len(self._selected_entry_ids) <= 1 or entry_id not in self._selected_entry_ids:
            return

        leader_entry = next((item for item in self._entries if item.entry_id == entry_id), None)
        leader_widget = self._widgets.get(entry_id)
        if leader_entry is None or leader_widget is None:
            return

        has_selected_sections = any(
            item.is_section and item.entry_id in self._selected_entry_ids for item in self._entries
        )
        if has_selected_sections:
            if leader_entry.is_section:
                if leader_widget.x() != constants.CANVAS_PADDING:
                    leader_widget.move(constants.CANVAS_PADDING, leader_widget.y())
            elif leader_widget.x() != leader_entry.x:
                # Mixed section+tool moves are vertical-only.
                leader_widget.move(leader_entry.x, leader_widget.y())

        delta_x = leader_widget.x() - leader_entry.x
        delta_y = leader_widget.y() - leader_entry.y
        if has_selected_sections:
            delta_x = 0

        selected_entries = [
            item for item in self._entries if item.entry_id in self._selected_entry_ids
        ]
        if not selected_entries:
            return

        min_selected_x = min(entry.x for entry in selected_entries)
        min_selected_y = min(entry.y for entry in selected_entries)
        if min_selected_x + delta_x < constants.CANVAS_PADDING:
            delta_x = constants.CANVAS_PADDING - min_selected_x
        if min_selected_y + delta_y < constants.CANVAS_PADDING:
            delta_y = constants.CANVAS_PADDING - min_selected_y

        expected_leader_x = (
            constants.CANVAS_PADDING if leader_entry.is_section else leader_entry.x + delta_x
        )
        expected_leader_y = max(constants.CANVAS_PADDING, leader_entry.y + delta_y)
        if leader_widget.x() != expected_leader_x or leader_widget.y() != expected_leader_y:
            leader_widget.move(expected_leader_x, expected_leader_y)

        if delta_x == 0 and delta_y == 0:
            return

        for selected_id in self._selected_entry_ids:
            if selected_id == entry_id:
                continue
            follower_entry = next(
                (item for item in self._entries if item.entry_id == selected_id), None
            )
            follower_widget = self._widgets.get(selected_id)
            if (
                follower_entry is None
                or follower_widget is None
                or not follower_widget.isVisible()
            ):
                continue

            if follower_entry.is_section:
                target_x = constants.CANVAS_PADDING
                target_y = follower_entry.y + delta_y
            else:
                target_x = follower_entry.x + delta_x
                target_y = follower_entry.y + delta_y
            follower_widget.move(target_x, target_y)

        if has_selected_sections:
            for selected_id in self._selected_entry_ids:
                selected_entry = next(
                    (item for item in self._entries if item.entry_id == selected_id),
                    None,
                )
                if selected_entry is None or not selected_entry.is_section:
                    continue
                self._on_section_move_live(selected_id)

        self._update_canvas_size()

    def _finalize_group_move(self, anchor_entry_id: str) -> None:
        selected_entries = [
            item for item in self._entries if item.entry_id in self._selected_entry_ids
        ]
        if not selected_entries:
            return

        has_selected_sections = any(entry.is_section for entry in selected_entries)
        has_selected_tools = any(entry.is_tool for entry in selected_entries)
        if has_selected_sections and has_selected_tools:
            self._finalize_mixed_group_move(anchor_entry_id, selected_entries)
            return
        if has_selected_tools and not has_selected_sections:
            self._finalize_tools_group_move(anchor_entry_id, selected_entries)
            return

        for entry in selected_entries:
            widget = self._widgets.get(entry.entry_id)
            if widget is None:
                continue
            if entry.is_section:
                entry.x = constants.CANVAS_PADDING
                entry.y = max(constants.CANVAS_PADDING, widget.y())
            else:
                entry.x = max(constants.CANVAS_PADDING, widget.x())
                entry.y = max(constants.CANVAS_PADDING, widget.y())

        moved_sections = sorted(
            (entry for entry in selected_entries if entry.is_section),
            key=lambda item: (item.y, item.title.lower()),
        )
        for section_entry in moved_sections:
            section_entry.y = self._layout_engine.snap_section_position(
                self._entries,
                section_entry.y,
                exclude_entry_id=section_entry.entry_id,
            )
            self._push_tools_below_section(section_entry.y)

        moved_tools = sorted(
            (entry for entry in selected_entries if entry.is_tool),
            key=lambda item: (item.y, item.x, item.title.lower()),
        )
        for tool_entry in moved_tools:
            snapped_x, snapped_y = self._layout_engine.snap_tool_position(
                self._entries,
                tool_entry.x,
                tool_entry.y,
                exclude_entry_id=tool_entry.entry_id,
            )
            tool_entry.x, tool_entry.y = snapped_x, snapped_y

        self._apply_geometry(compact_tools=False)
        self._update_canvas_size()

        anchor_entry = next(
            (item for item in self._entries if item.entry_id == anchor_entry_id), None
        )
        if anchor_entry is not None:
            self.entry_moved.emit(anchor_entry.entry_id, anchor_entry.x, anchor_entry.y)

    def _finalize_tools_group_move(
        self,
        anchor_entry_id: str,
        selected_entries: list[ToolboxEntry],
    ) -> None:
        anchor_entry = next(
            (item for item in selected_entries if item.entry_id == anchor_entry_id and item.is_tool),
            None,
        )
        anchor_widget = self._widgets.get(anchor_entry_id)
        if anchor_entry is None or anchor_widget is None:
            return

        selected_tool_ids = {entry.entry_id for entry in selected_entries if entry.is_tool}
        if not selected_tool_ids:
            return

        selected_tools = [entry for entry in selected_entries if entry.is_tool]
        anchor_target_x, anchor_target_y = self._single_tool_drop_target(
            anchor_entry.entry_id,
            anchor_widget.x(),
            anchor_widget.y(),
        )
        delta_x = anchor_target_x - anchor_entry.x
        delta_y = anchor_target_y - anchor_entry.y

        min_x = min(entry.x for entry in selected_tools)
        min_y = min(entry.y for entry in selected_tools)
        if min_x + delta_x < constants.CANVAS_PADDING:
            delta_x = constants.CANVAS_PADDING - min_x
        if min_y + delta_y < constants.CANVAS_PADDING:
            delta_y = constants.CANVAS_PADDING - min_y

        for entry in selected_entries:
            if not entry.is_tool:
                continue
            entry.x = max(constants.CANVAS_PADDING, entry.x + delta_x)
            entry.y = max(constants.CANVAS_PADDING, entry.y + delta_y)

        self._resolve_selected_tools_as_group(selected_tool_ids)
        self._apply_geometry(compact_tools=False)
        self._update_canvas_size()
        self.entry_moved.emit(anchor_entry.entry_id, anchor_entry.x, anchor_entry.y)

    def _single_tool_drop_target(self, entry_id: str, x: int, y: int) -> tuple[int, int]:
        if not self._auto_compact_left:
            return self._layout_engine.snap_tool_position(
                self._entries,
                x,
                y,
                exclude_entry_id=entry_id,
            )

        other_entries = [item for item in self._entries if item.entry_id != entry_id]
        insertion_y, _, _ = self._layout_engine.insertion_row_y(other_entries, y, below=False)
        return max(constants.CANVAS_PADDING, x), insertion_y

    def _finalize_mixed_group_move(
        self,
        anchor_entry_id: str,
        selected_entries: list[ToolboxEntry],
    ) -> None:
        anchor_entry = next(
            (item for item in selected_entries if item.entry_id == anchor_entry_id),
            None,
        )
        anchor_widget = self._widgets.get(anchor_entry_id)
        if anchor_entry is None or anchor_widget is None:
            return

        delta_x = 0
        delta_y = anchor_widget.y() - anchor_entry.y

        for entry in selected_entries:
            if entry.is_section:
                entry.x = constants.CANVAS_PADDING
                entry.y = max(constants.CANVAS_PADDING, entry.y + delta_y)
            else:
                entry.x = max(constants.CANVAS_PADDING, entry.x + delta_x)
                entry.y = max(constants.CANVAS_PADDING, entry.y + delta_y)

        moved_sections = sorted(
            (entry for entry in selected_entries if entry.is_section),
            key=lambda item: (item.y, item.title.lower()),
        )
        section_snap_deltas: dict[str, int] = {}
        for section_entry in moved_sections:
            before_snap_y = section_entry.y
            section_entry.y = self._layout_engine.snap_section_position(
                self._entries,
                section_entry.y,
                exclude_entry_id=section_entry.entry_id,
            )
            section_snap_deltas[section_entry.entry_id] = section_entry.y - before_snap_y
            self._push_tools_below_section(
                section_entry.y,
                excluded_entry_ids=self._selected_entry_ids,
            )

        selected_tool_ids = {entry.entry_id for entry in selected_entries if entry.is_tool}
        tool_snap_delta = 0
        if section_snap_deltas:
            if anchor_entry.is_section and anchor_entry.entry_id in section_snap_deltas:
                tool_snap_delta = section_snap_deltas[anchor_entry.entry_id]
            elif len(section_snap_deltas) == 1:
                tool_snap_delta = next(iter(section_snap_deltas.values()))
        if tool_snap_delta != 0 and selected_tool_ids:
            for entry in selected_entries:
                if not entry.is_tool:
                    continue
                entry.y = max(constants.CANVAS_PADDING, entry.y + tool_snap_delta)

        self._resolve_selected_tools_as_group(selected_tool_ids)

        self._apply_geometry(compact_tools=False)
        self._update_canvas_size()
        self.entry_moved.emit(anchor_entry.entry_id, anchor_entry.x, anchor_entry.y)

    def _resolve_selected_tools_as_group(
        self,
        selected_tool_ids: set[str],
    ) -> None:
        if not selected_tool_ids:
            return

        row_height = self._layout_engine.tool_cell_size()[1]
        section_bands = self._layout_engine.section_bands(self._entries)
        occupied_rects = [
            self._layout_engine.tool_rect_at(entry.x, entry.y)
            for entry in self._entries
            if entry.is_tool and entry.entry_id not in selected_tool_ids
        ]
        selected_tools = sorted(
            (
                entry
                for entry in self._entries
                if entry.is_tool and entry.entry_id in selected_tool_ids
            ),
            key=lambda item: (item.y, item.x, item.title.lower()),
        )
        if not selected_tools:
            return

        for tool_entry in selected_tools:
            tool_entry.y = max(constants.CANVAS_PADDING, tool_entry.y)

        guard = 0
        while guard < 2000:
            selected_rects = [
                self._layout_engine.tool_rect_at(entry.x, entry.y) for entry in selected_tools
            ]
            has_conflict = any(
                rect.intersects(band) for rect in selected_rects for band in section_bands
            ) or any(
                rect.intersects(occupied_rect)
                for rect in selected_rects
                for occupied_rect in occupied_rects
            )
            if not has_conflict:
                break
            for tool_entry in selected_tools:
                tool_entry.y += row_height
            guard += 1
