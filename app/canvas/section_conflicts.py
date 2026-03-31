#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Section protection conflict helpers for canvas entries."""

from __future__ import annotations

from typing import Optional

from app import constants
from app.canvas.layout_engine import CanvasLayoutEngine
from app.domain.models import ToolboxEntry


def section_drop_intersects_tools(
    entries: list[ToolboxEntry],
    layout_engine: CanvasLayoutEngine,
    section_y: int,
    exclude_entry_id: Optional[str] = None,
) -> bool:
    """Return whether a section at ``section_y`` would overlap any tool tile."""
    protected_rect = layout_engine.section_protected_rect_at(section_y)
    for item in entries:
        if not item.is_tool or item.entry_id == exclude_entry_id:
            continue
        if layout_engine.tool_rect_at(item.x, item.y).intersects(protected_rect):
            return True
    return False


def nearest_non_conflicting_section_y(
    entries: list[ToolboxEntry],
    layout_engine: CanvasLayoutEngine,
    section_y: int,
    exclude_entry_id: Optional[str] = None,
) -> int:
    """Shift a section down by section steps until no tool overlap remains."""
    safe_y = section_y
    step = layout_engine.section_step()
    guard = 0
    while (
        section_drop_intersects_tools(
            entries, layout_engine, safe_y, exclude_entry_id=exclude_entry_id
        )
        and guard < 400
    ):
        safe_y += step
        guard += 1
    return safe_y


def push_tools_below_section(
    entries: list[ToolboxEntry],
    layout_engine: CanvasLayoutEngine,
    section_y: int,
    excluded_entry_ids: set[str] | None = None,
) -> bool:
    """Move overlapping tools below a section's protected zone."""
    excluded = excluded_entry_ids or set()
    protected_rect = layout_engine.section_protected_rect_at(section_y)
    insertion_y = protected_rect.bottom() + 1
    row_height = layout_engine.tool_cell_size()[1]
    shifted = False
    for item in entries:
        if not item.is_tool:
            continue
        if item.entry_id in excluded:
            continue
        rect = layout_engine.tool_rect_at(item.x, item.y)
        if not rect.intersects(protected_rect):
            continue
        item.y = max(item.y, insertion_y)
        while layout_engine.tool_rect_at(item.x, item.y).intersects(protected_rect):
            item.y += row_height
        shifted = True
    return shifted


def resolve_section_protection_conflicts(
    entries: list[ToolboxEntry],
    layout_engine: CanvasLayoutEngine,
) -> bool:
    """Iteratively resolve section/tool overlaps until stable or guard limit is hit."""
    shifted_any = False
    guard = 0
    while guard < 32:
        shifted_this_round = False
        sections = sorted(
            (entry for entry in entries if entry.is_section),
            key=lambda item: (item.y, item.title.lower()),
        )
        for section in sections:
            if push_tools_below_section(entries, layout_engine, section.y):
                shifted_this_round = True
                shifted_any = True
        if not shifted_this_round:
            break
        guard += 1
    return shifted_any


def segment_index_for_y_in_ranges(
    y: int,
    segments: list[tuple[int, Optional[int]]],
) -> int:
    """Return the segment index containing ``y`` within ``segments``."""
    if not segments:
        return 0
    for index, (start_y, end_y) in enumerate(segments):
        if y < start_y:
            return index
        if end_y is None or y <= end_y:
            return index
    return len(segments) - 1


def shift_tools_for_segment_start_delta(
    entries: list[ToolboxEntry],
    previous_segments: list[tuple[int, Optional[int]]],
    updated_segments: list[tuple[int, Optional[int]]],
) -> bool:
    """Shift tools by segment-start deltas when segment boundaries changed."""
    if not previous_segments or len(previous_segments) != len(updated_segments):
        return False

    shifted_any = False
    segment_start_deltas = [
        updated_start - previous_start
        for (previous_start, _), (updated_start, _) in zip(previous_segments, updated_segments)
    ]
    if not any(delta != 0 for delta in segment_start_deltas):
        return False

    for entry in entries:
        if not entry.is_tool:
            continue
        segment_index = segment_index_for_y_in_ranges(entry.y, previous_segments)
        delta = segment_start_deltas[segment_index]
        if delta == 0:
            continue
        entry.y = max(constants.CANVAS_PADDING, entry.y + delta)
        shifted_any = True
    return shifted_any
