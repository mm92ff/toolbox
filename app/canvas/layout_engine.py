#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canvas layout metrics and snap/grid calculations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from PySide6 import QtCore, QtGui

from app import constants
from app.domain.models import ToolboxEntry


@dataclass(frozen=True)
class TileMetrics:
    icon_size: int
    font_pixel_size: int
    horizontal_padding: int
    vertical_padding: int
    content_spacing: int
    title_height: int
    tile_width: int
    tile_height: int
    border_radius: int

    @property
    def tile_size(self) -> QtCore.QSize:
        return QtCore.QSize(self.tile_width, self.tile_height)


@dataclass(frozen=True)
class SectionMetrics:
    font_pixel_size: int
    line_thickness: int
    vertical_padding: int
    horizontal_spacing: int
    title_horizontal_padding: int
    height: int


def clamp(value: int, minimum: int, maximum: int) -> int:
    """Clamp ``value`` to the inclusive range ``[minimum, maximum]``."""
    return max(minimum, min(maximum, value))


def build_tile_metrics(icon_size: int) -> TileMetrics:
    """Derive tile geometry and typography metrics from the requested icon size."""
    safe_icon_size = clamp(icon_size, constants.MIN_ICON_SIZE, constants.MAX_ICON_SIZE)
    font_pixel_size = clamp(round(safe_icon_size * 0.18), 9, 18)
    horizontal_padding = clamp(round(safe_icon_size * 0.16), 6, 22)
    vertical_padding = clamp(round(safe_icon_size * 0.14), 5, 20)
    content_spacing = clamp(round(safe_icon_size * 0.10), 3, 14)
    title_height = clamp(round(font_pixel_size * 2.7), 22, 50)
    tile_width = clamp(
        safe_icon_size + (2 * horizontal_padding) + max(24, round(font_pixel_size * 4.8)),
        96,
        240,
    )
    tile_height = safe_icon_size + title_height + (2 * vertical_padding) + content_spacing
    border_radius = clamp(round(safe_icon_size * 0.18), 10, 24)
    return TileMetrics(
        icon_size=safe_icon_size,
        font_pixel_size=font_pixel_size,
        horizontal_padding=horizontal_padding,
        vertical_padding=vertical_padding,
        content_spacing=content_spacing,
        title_height=title_height,
        tile_width=tile_width,
        tile_height=tile_height,
        border_radius=border_radius,
    )


def build_section_metrics(font_size: int, line_thickness: int) -> SectionMetrics:
    """Derive section header metrics from font size and line thickness inputs."""
    safe_font_size = clamp(
        font_size, constants.MIN_SECTION_FONT_SIZE, constants.MAX_SECTION_FONT_SIZE
    )
    safe_line_thickness = clamp(
        line_thickness,
        constants.MIN_SECTION_LINE_THICKNESS,
        constants.MAX_SECTION_LINE_THICKNESS,
    )
    vertical_padding = clamp(round(safe_font_size * 0.55), 6, 18)
    horizontal_spacing = clamp(round(safe_font_size * 0.75), 8, 26)
    title_horizontal_padding = clamp(round(safe_font_size * 0.9), 10, 28)
    height = safe_font_size + (2 * vertical_padding) + max(4, safe_line_thickness + 2)
    return SectionMetrics(
        font_pixel_size=safe_font_size,
        line_thickness=safe_line_thickness,
        vertical_padding=vertical_padding,
        horizontal_spacing=horizontal_spacing,
        title_horizontal_padding=title_horizontal_padding,
        height=height,
    )


class CanvasLayoutEngine:
    """Pure layout/snap calculations for tool and section entries."""

    def __init__(self) -> None:
        self._icon_size = constants.DEFAULT_ICON_SIZE
        self._grid_spacing_x = constants.DEFAULT_GRID_SPACING_X
        self._grid_spacing_y = constants.DEFAULT_GRID_SPACING_Y
        self._section_font_size = constants.DEFAULT_SECTION_FONT_SIZE
        self._section_line_thickness = constants.DEFAULT_SECTION_LINE_THICKNESS
        self._section_gap_above = constants.DEFAULT_SECTION_PROTECTED_GAP_ABOVE
        self._section_gap_below = constants.DEFAULT_SECTION_PROTECTED_GAP_BELOW
        self._section_line_color = constants.DEFAULT_SECTION_LINE_COLOR
        self._viewport_width = 900

    @property
    def icon_size(self) -> int:
        return self._icon_size

    @property
    def section_font_size(self) -> int:
        return self._section_font_size

    @property
    def section_line_thickness(self) -> int:
        return self._section_line_thickness

    @property
    def section_line_color(self) -> str:
        return self._section_line_color

    def set_viewport_width(self, viewport_width: int) -> None:
        self._viewport_width = max(480, viewport_width)

    def configure(
        self,
        icon_size: int,
        grid_spacing_x: int,
        grid_spacing_y: int,
        section_font_size: int,
        section_line_thickness: int,
        section_gap: int,
        section_line_color: str,
        *,
        section_gap_above: int | None = None,
        section_gap_below: int | None = None,
    ) -> None:
        self._icon_size = clamp(icon_size, constants.MIN_ICON_SIZE, constants.MAX_ICON_SIZE)
        self._grid_spacing_x = clamp(
            grid_spacing_x, constants.MIN_GRID_SPACING, constants.MAX_GRID_SPACING
        )
        self._grid_spacing_y = clamp(
            grid_spacing_y, constants.MIN_GRID_SPACING, constants.MAX_GRID_SPACING
        )
        self._section_font_size = clamp(
            section_font_size, constants.MIN_SECTION_FONT_SIZE, constants.MAX_SECTION_FONT_SIZE
        )
        self._section_line_thickness = clamp(
            section_line_thickness,
            constants.MIN_SECTION_LINE_THICKNESS,
            constants.MAX_SECTION_LINE_THICKNESS,
        )
        fallback_gap_above = clamp(
            section_gap,
            constants.MIN_SECTION_PROTECTED_GAP_ABOVE,
            constants.MAX_SECTION_PROTECTED_GAP_ABOVE,
        )
        fallback_gap_below = clamp(
            section_gap,
            constants.MIN_SECTION_PROTECTED_GAP_BELOW,
            constants.MAX_SECTION_PROTECTED_GAP_BELOW,
        )
        self._section_gap_above = clamp(
            fallback_gap_above if section_gap_above is None else int(section_gap_above),
            constants.MIN_SECTION_PROTECTED_GAP_ABOVE,
            constants.MAX_SECTION_PROTECTED_GAP_ABOVE,
        )
        self._section_gap_below = clamp(
            fallback_gap_below if section_gap_below is None else int(section_gap_below),
            constants.MIN_SECTION_PROTECTED_GAP_BELOW,
            constants.MAX_SECTION_PROTECTED_GAP_BELOW,
        )
        color = QtGui.QColor((section_line_color or "").strip())
        self._section_line_color = (
            color.name() if color.isValid() else constants.DEFAULT_SECTION_LINE_COLOR
        )

    def tool_tile_size(self) -> QtCore.QSize:
        return build_tile_metrics(self._icon_size).tile_size

    def section_height(self) -> int:
        return build_section_metrics(self._section_font_size, self._section_line_thickness).height

    def tool_cell_size(self) -> tuple[int, int]:
        tile_size = self.tool_tile_size()
        return tile_size.width() + max(0, self._grid_spacing_x), tile_size.height() + max(
            0, self._grid_spacing_y
        )

    def section_step(self) -> int:
        return self.section_height() + max(8, self._grid_spacing_y)

    def content_width(self) -> int:
        return max(self._viewport_width - (2 * constants.CANVAS_PADDING), 320)

    def tool_rect_at(self, x: int, y: int) -> QtCore.QRect:
        size = self.tool_tile_size()
        return QtCore.QRect(x, y, size.width(), size.height())

    def section_rect_at(self, y: int) -> QtCore.QRect:
        return QtCore.QRect(
            constants.CANVAS_PADDING, y, self.content_width(), self.section_height()
        )

    def section_protected_rect_at(self, y: int) -> QtCore.QRect:
        rect = self.section_rect_at(y)
        return rect.adjusted(0, -self._section_gap_above, 0, self._section_gap_below)

    def tool_cell_from_position(self, x: int, y: int) -> tuple[int, int]:
        cell_w, cell_h = self.tool_cell_size()
        col = max(0, round((x - constants.CANVAS_PADDING) / max(1, cell_w)))
        row = max(0, round((y - constants.CANVAS_PADDING) / max(1, cell_h)))
        return col, row

    def tool_position_from_cell(self, col: int, row: int) -> tuple[int, int]:
        cell_w, cell_h = self.tool_cell_size()
        return constants.CANVAS_PADDING + col * cell_w, constants.CANVAS_PADDING + row * cell_h

    def section_row_from_y(self, y: int) -> int:
        step = self.section_step()
        return max(0, round((y - constants.CANVAS_PADDING) / max(1, step)))

    def section_y_from_row(self, row: int) -> int:
        return constants.CANVAS_PADDING + row * self.section_step()

    def section_rows_in_use(
        self, entries: Iterable[ToolboxEntry], exclude_entry_id: Optional[str] = None
    ) -> set[int]:
        rows: set[int] = set()
        for entry in entries:
            if not entry.is_section or entry.entry_id == exclude_entry_id:
                continue
            rows.add(self.section_row_from_y(entry.y))
        return rows

    def snap_section_position(
        self, entries: Iterable[ToolboxEntry], y: int, exclude_entry_id: Optional[str] = None
    ) -> int:
        target_row = self.section_row_from_y(y)
        used_rows = self.section_rows_in_use(entries, exclude_entry_id)
        offsets = [0]
        for delta in range(1, 256):
            offsets.extend((delta, -delta))
        for offset in offsets:
            row = max(0, target_row + offset)
            if row not in used_rows:
                return self.section_y_from_row(row)
        return self.section_y_from_row(target_row + len(used_rows) + 1)

    def section_bands(
        self, entries: Iterable[ToolboxEntry], exclude_entry_id: Optional[str] = None
    ) -> list[QtCore.QRect]:
        bands: list[QtCore.QRect] = []
        for entry in entries:
            if not entry.is_section or entry.entry_id == exclude_entry_id:
                continue
            bands.append(self.section_protected_rect_at(entry.y))
        return bands

    def occupied_tool_cells(
        self, entries: Iterable[ToolboxEntry], exclude_entry_id: Optional[str] = None
    ) -> set[tuple[int, int]]:
        cells: set[tuple[int, int]] = set()
        for entry in entries:
            if not entry.is_tool or entry.entry_id == exclude_entry_id:
                continue
            cells.add(self.tool_cell_from_position(entry.x, entry.y))
        return cells

    def columns_hint(self) -> int:
        cell_w, _ = self.tool_cell_size()
        return max(1, self.content_width() // max(1, cell_w))

    def _tool_rects(
        self,
        entries: Iterable[ToolboxEntry],
        exclude_entry_id: Optional[str] = None,
    ) -> list[QtCore.QRect]:
        rects: list[QtCore.QRect] = []
        for entry in entries:
            if not entry.is_tool or entry.entry_id == exclude_entry_id:
                continue
            rects.append(self.tool_rect_at(entry.x, entry.y))
        return rects

    def _segments_from_bands(
        self, section_bands: list[QtCore.QRect]
    ) -> list[tuple[int, Optional[int]]]:
        segments: list[tuple[int, Optional[int]]] = []
        start_y = constants.CANVAS_PADDING
        for band in sorted(section_bands, key=lambda rect: rect.top()):
            end_y = band.top() - 1
            segments.append((start_y, end_y))
            start_y = band.bottom() + 1
        segments.append((start_y, None))
        return segments

    def _preferred_segment_index(
        self,
        segments: list[tuple[int, Optional[int]]],
        target_y: int,
    ) -> int:
        if not segments:
            return 0
        for index, (start_y, end_y) in enumerate(segments):
            if target_y < start_y:
                return index
            if end_y is None or target_y <= end_y:
                return index
        return len(segments) - 1

    def insertion_row_y(
        self,
        entries: Iterable[ToolboxEntry],
        target_y: int,
        below: bool,
    ) -> tuple[int, int, Optional[int]]:
        section_bands = self.section_bands(entries)
        segments = self._segments_from_bands(section_bands)
        segment_index = self._preferred_segment_index(segments, target_y)
        segment_start, segment_end = segments[segment_index]
        cell_h = self.tool_cell_size()[1]
        local_row = max(0, (target_y - segment_start) // max(1, cell_h))
        if below:
            local_row += 1
        insertion_y = segment_start + local_row * cell_h
        if segment_end is not None:
            insertion_y = min(insertion_y, segment_end + 1)
        return insertion_y, segment_start, segment_end

    def segment_index_for_y(
        self,
        entries: Iterable[ToolboxEntry],
        target_y: int,
    ) -> int:
        segments = self._segments_from_bands(self.section_bands(entries))
        return self._preferred_segment_index(segments, target_y)

    def segment_ranges(
        self,
        entries: Iterable[ToolboxEntry],
        exclude_entry_id: Optional[str] = None,
    ) -> list[tuple[int, Optional[int]]]:
        return self._segments_from_bands(self.section_bands(entries, exclude_entry_id))

    def find_nearest_free_cell(
        self,
        target_col: int,
        target_y: int,
        occupied_rects: list[QtCore.QRect],
        section_bands: list[QtCore.QRect],
    ) -> tuple[int, int]:
        viewport_max_col_index = max(0, self.columns_hint() - 1)
        existing_max_col_index = max(
            (self.tool_cell_from_position(rect.x(), rect.y())[0] for rect in occupied_rects),
            default=0,
        )
        max_col_index = max(viewport_max_col_index, existing_max_col_index, target_col)
        target_col = clamp(target_col, 0, max_col_index)

        col_offsets = [0]
        for delta in range(1, max_col_index + 2):
            col_offsets.extend((delta, -delta))

        cell_h = self.tool_cell_size()[1]
        segments = self._segments_from_bands(section_bands)
        preferred_segment_idx = self._preferred_segment_index(segments, target_y)
        for segment_start, segment_end in segments[preferred_segment_idx:]:
            if segment_end is not None and segment_end < segment_start:
                continue

            local_target_row = max(0, round((target_y - segment_start) / max(1, cell_h)))
            max_rows = 600
            if segment_end is not None:
                max_rows = max(0, ((segment_end - segment_start) // max(1, cell_h)) + 1)
            for row_delta in range(0, max_rows):
                row = max(0, local_target_row + row_delta)
                y = segment_start + row * cell_h
                if segment_end is not None and y > segment_end:
                    continue
                for col_offset in col_offsets:
                    col = target_col + col_offset
                    if col < 0 or col > max_col_index:
                        continue
                    x, _ = self.tool_position_from_cell(col, 0)
                    rect = self.tool_rect_at(x, y)
                    if any(rect.intersects(band) for band in section_bands):
                        continue
                    if any(rect.intersects(occupied_rect) for occupied_rect in occupied_rects):
                        continue
                    return x, y

        fallback_y = segments[-1][0] if segments else constants.CANVAS_PADDING
        fallback_x, _ = self.tool_position_from_cell(target_col, 0)
        return fallback_x, max(constants.CANVAS_PADDING, fallback_y)

    def snap_tool_position(
        self,
        entries: Iterable[ToolboxEntry],
        x: int,
        y: int,
        exclude_entry_id: Optional[str] = None,
    ) -> tuple[int, int]:
        target_col, _ = self.tool_cell_from_position(x, y)
        return self.find_nearest_free_cell(
            target_col,
            y,
            self._tool_rects(entries, exclude_entry_id),
            self.section_bands(entries, exclude_entry_id),
        )

    def find_next_free_tool_position(self, entries: Iterable[ToolboxEntry]) -> tuple[int, int]:
        occupied = self._tool_rects(entries)
        bands = self.section_bands(entries)
        return self.find_nearest_free_cell(0, 0, occupied, bands)

    def find_next_section_y(self, entries: Iterable[ToolboxEntry]) -> int:
        max_bottom = constants.CANVAS_PADDING
        tile_height = self.tool_tile_size().height()
        section_height = self.section_height()
        for entry in entries:
            if entry.is_tool:
                max_bottom = max(max_bottom, entry.y + tile_height)
            else:
                max_bottom = max(max_bottom, entry.y + section_height)
        gap_hint = max(self._section_gap_above, self._section_gap_below)
        return self.snap_section_position(entries, max_bottom + max(8, gap_hint + 8))
