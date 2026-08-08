#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Widget-independent responsive layout calculations for canvas entries."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResponsiveItem:
    entry_id: str
    is_section: bool
    x: int
    y: int
    source_index: int


@dataclass(frozen=True, slots=True)
class ResponsiveRect:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class ResponsiveLayoutResult:
    rects: dict[str, ResponsiveRect]
    content_width: int
    content_height: int
    columns: int


def build_responsive_layout(
    items: list[ResponsiveItem],
    *,
    viewport_width: int,
    tile_width: int,
    tile_height: int,
    spacing_x: int,
    spacing_y: int,
    padding: int,
    section_height: int,
    section_gap_above: int,
    section_gap_below: int,
    minimum_content_height: int = 420,
) -> ResponsiveLayoutResult:
    """Return visual rectangles without modifying the supplied items.

    Canonical coordinates are used only to derive a stable logical order. Sections
    split the tool stream into independent row-major groups.
    """

    safe_viewport = max(1, int(viewport_width))
    tile_width = max(1, int(tile_width))
    tile_height = max(1, int(tile_height))
    spacing_x = max(0, int(spacing_x))
    spacing_y = max(0, int(spacing_y))
    padding = max(0, int(padding))
    available_width = max(1, safe_viewport - (2 * padding))
    columns = max(1, (available_width + spacing_x) // (tile_width + spacing_x))
    content_width = max(tile_width, available_width)

    ordered = sorted(items, key=lambda item: (item.y, item.x, item.source_index))
    rects: dict[str, ResponsiveRect] = {}
    current_y = padding
    pending_tools: list[ResponsiveItem] = []

    def flush_tools() -> None:
        nonlocal current_y
        if not pending_tools:
            return
        for index, item in enumerate(pending_tools):
            row, column = divmod(index, columns)
            rects[item.entry_id] = ResponsiveRect(
                padding + column * (tile_width + spacing_x),
                current_y + row * (tile_height + spacing_y),
                tile_width,
                tile_height,
            )
        row_count = (len(pending_tools) + columns - 1) // columns
        current_y += row_count * tile_height + max(0, row_count - 1) * spacing_y
        pending_tools.clear()

    for item in ordered:
        if not item.is_section:
            pending_tools.append(item)
            continue
        flush_tools()
        current_y += max(0, int(section_gap_above))
        rects[item.entry_id] = ResponsiveRect(
            padding,
            current_y,
            content_width,
            max(1, int(section_height)),
        )
        current_y += max(1, int(section_height)) + max(0, int(section_gap_below))

    flush_tools()
    content_height = max(int(minimum_content_height), current_y + padding)
    return ResponsiveLayoutResult(
        rects=rects,
        content_width=content_width + (2 * padding),
        content_height=content_height,
        columns=columns,
    )
