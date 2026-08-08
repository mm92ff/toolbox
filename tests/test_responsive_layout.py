from __future__ import annotations

import os
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtTest, QtWidgets

from app import constants
from app.canvas.responsive_layout import ResponsiveItem, build_responsive_layout
from app.canvas.toolbox_canvas import CanvasSurface, ToolboxCanvas
from app.domain.models import ToolboxEntry
from app.features.entries.controller_canvas import update_window_minimum_width


def _items(count: int) -> list[ResponsiveItem]:
    return [
        ResponsiveItem(str(index), False, index * 100, 18, index)
        for index in range(count)
    ]


def test_responsive_layout_wraps_from_four_to_two_to_one_columns() -> None:
    original = _items(5)
    original_values = list(original)

    wide = build_responsive_layout(
        original,
        viewport_width=482,
        tile_width=100,
        tile_height=100,
        spacing_x=10,
        spacing_y=12,
        padding=16,
        section_height=40,
        section_gap_above=8,
        section_gap_below=9,
    )
    medium = build_responsive_layout(
        original,
        viewport_width=262,
        tile_width=100,
        tile_height=100,
        spacing_x=10,
        spacing_y=12,
        padding=16,
        section_height=40,
        section_gap_above=8,
        section_gap_below=9,
    )
    narrow = build_responsive_layout(
        original,
        viewport_width=130,
        tile_width=100,
        tile_height=100,
        spacing_x=10,
        spacing_y=12,
        padding=16,
        section_height=40,
        section_gap_above=8,
        section_gap_below=9,
    )

    assert wide.columns == 4
    assert medium.columns == 2
    assert narrow.columns == 1
    assert wide.rects["4"].y > wide.rects["0"].y
    assert medium.rects["2"].y > medium.rects["0"].y
    assert narrow.rects["1"].y > narrow.rects["0"].y
    assert original == original_values


def test_sections_split_groups_and_span_available_width() -> None:
    items = [
        ResponsiveItem("before", False, 18, 18, 0),
        ResponsiveItem("section", True, 18, 200, 1),
        ResponsiveItem("after-a", False, 18, 300, 2),
        ResponsiveItem("after-b", False, 118, 300, 3),
    ]
    result = build_responsive_layout(
        items,
        viewport_width=360,
        tile_width=100,
        tile_height=100,
        spacing_x=10,
        spacing_y=12,
        padding=18,
        section_height=42,
        section_gap_above=14,
        section_gap_below=16,
    )

    assert result.columns == 3
    assert result.rects["section"].width == 324
    assert result.rects["section"].y >= result.rects["before"].y + 100 + 14
    assert result.rects["after-a"].y >= result.rects["section"].y + 42 + 16
    assert result.rects["after-a"].y == result.rects["after-b"].y


def test_exact_breakpoint_and_empty_input_are_valid() -> None:
    exact_width = (2 * 16) + (3 * 100) + (2 * 10)
    exact = build_responsive_layout(
        _items(3),
        viewport_width=exact_width,
        tile_width=100,
        tile_height=100,
        spacing_x=10,
        spacing_y=12,
        padding=16,
        section_height=40,
        section_gap_above=8,
        section_gap_below=9,
    )
    below = build_responsive_layout(
        _items(3),
        viewport_width=exact_width - 1,
        tile_width=100,
        tile_height=100,
        spacing_x=10,
        spacing_y=12,
        padding=16,
        section_height=40,
        section_gap_above=8,
        section_gap_below=9,
    )
    empty = build_responsive_layout(
        [],
        viewport_width=0,
        tile_width=100,
        tile_height=100,
        spacing_x=10,
        spacing_y=12,
        padding=16,
        section_height=40,
        section_gap_above=8,
        section_gap_below=9,
    )

    assert exact.columns == 3
    assert below.columns == 2
    assert empty.columns == 1
    assert empty.rects == {}
    assert empty.content_height == 420


def _surface_entries() -> list[ToolboxEntry]:
    return [
        ToolboxEntry(
            title=f"Tool {index}",
            kind=constants.ENTRY_KIND_TOOL,
            path=f"/tmp/tool-{index}",
            x=constants.CANVAS_PADDING + index * 150,
            y=constants.CANVAS_PADDING,
            entry_id=f"tool-{index}",
        )
        for index in range(4)
    ]


def _set_surface_entries(
    surface: CanvasSurface,
    entries: list[ToolboxEntry],
    width: int,
    responsive: bool,
    hidden_entry_ids: set[str] | None = None,
) -> None:
    surface.set_entries(
        entries=entries,
        icon_provider=QtWidgets.QFileIconProvider(),
        icon_size=constants.DEFAULT_ICON_SIZE,
        tile_frame_enabled=constants.DEFAULT_TILE_FRAME_ENABLED,
        tile_frame_thickness=constants.DEFAULT_TILE_FRAME_THICKNESS,
        tile_frame_color=constants.DEFAULT_TILE_FRAME_COLOR,
        tile_highlight_color=constants.DEFAULT_TILE_HIGHLIGHT_COLOR,
        grid_spacing_x=constants.DEFAULT_GRID_SPACING_X,
        grid_spacing_y=constants.DEFAULT_GRID_SPACING_Y,
        auto_compact_left=constants.DEFAULT_AUTO_COMPACT_LEFT,
        section_font_size=constants.DEFAULT_SECTION_FONT_SIZE,
        section_line_thickness=constants.DEFAULT_SECTION_LINE_THICKNESS,
        section_gap=constants.DEFAULT_SECTION_PROTECTED_GAP,
        section_line_color=constants.DEFAULT_SECTION_LINE_COLOR,
        selected_entry_ids=set(),
        hidden_entry_ids=hidden_entry_ids or set(),
        viewport_width=width,
        responsive_layout=responsive,
    )


def test_surface_resize_changes_only_visual_geometry() -> None:
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    entries = _surface_entries()
    canonical = [(entry.x, entry.y) for entry in entries]
    surface = CanvasSurface()
    _set_surface_entries(surface, entries, 700, True)
    wide_columns = surface.responsive_columns()
    surface.set_viewport_width(240)

    assert surface.responsive_columns() < wide_columns
    assert [(entry.x, entry.y) for entry in entries] == canonical
    assert all(not widget.movement_enabled() for widget in surface._widgets.values())

    surface.set_responsive_layout_enabled(False)
    assert [(widget.x(), widget.y()) for widget in surface._widgets.values()] == canonical
    assert all(widget.movement_enabled() for widget in surface._widgets.values())


def test_two_canvases_can_have_independent_responsive_column_counts() -> None:
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    shared_entries = _surface_entries()
    canonical = [(entry.x, entry.y) for entry in shared_entries]
    wide = CanvasSurface()
    narrow = CanvasSurface()
    _set_surface_entries(wide, shared_entries, 900, True)
    _set_surface_entries(narrow, shared_entries, 260, True)

    assert wide.responsive_columns() > narrow.responsive_columns()
    assert [(entry.x, entry.y) for entry in shared_entries] == canonical


def test_hidden_entry_leaves_no_responsive_grid_gap() -> None:
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    surface = CanvasSurface()
    _set_surface_entries(
        surface,
        _surface_entries(),
        700,
        True,
        hidden_entry_ids={"tool-1"},
    )

    first = surface._widgets["tool-0"].geometry()
    third = surface._widgets["tool-2"].geometry()
    assert not surface._widgets["tool-1"].isVisible()
    assert third.y() == first.y()
    assert third.x() == first.x() + first.width() + constants.DEFAULT_GRID_SPACING_X


def test_toolbox_canvas_disables_horizontal_scrollbar_in_responsive_mode() -> None:
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    canvas = ToolboxCanvas()
    _set_surface_entries(canvas.surface, _surface_entries(), 260, True)
    canvas._sync_scrollbar_policy()

    assert canvas.horizontalScrollBarPolicy() == QtCore.Qt.ScrollBarAlwaysOff


def test_resize_events_are_throttled_and_apply_the_last_width() -> None:
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    canvas = ToolboxCanvas()
    calls: list[int] = []
    original = canvas.surface.set_viewport_width

    def record(width: int) -> None:
        calls.append(width)
        original(width)

    canvas.surface.set_viewport_width = record  # type: ignore[method-assign]
    for width in range(300, 400):
        event = QtGui.QResizeEvent(QtCore.QSize(width, 500), QtCore.QSize(width - 1, 500))
        canvas.resizeEvent(event)
    QtTest.QTest.qWait(constants.RESPONSIVE_LAYOUT_INTERVAL_MS + 20)

    assert 1 <= len(calls) <= 2
    assert calls[-1] == canvas.viewport().width()


def test_same_column_resize_skips_full_reflow_but_resizes_sections() -> None:
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    entries = _surface_entries()
    entries.append(
        ToolboxEntry(
            title="Section",
            kind=constants.ENTRY_KIND_SECTION,
            x=constants.CANVAS_PADDING,
            y=300,
            entry_id="section",
        )
    )
    surface = CanvasSurface()
    _set_surface_entries(surface, entries, 700, True)
    initial_reflows = surface.responsive_reflow_count()
    initial_columns = surface.responsive_columns()
    initial_tool_geometry = surface._widgets["tool-0"].geometry()
    initial_section_width = surface._widgets["section"].width()

    surface.set_viewport_width(660)

    assert surface.responsive_columns() == initial_columns
    assert surface.responsive_reflow_count() == initial_reflows
    assert surface._widgets["tool-0"].geometry() == initial_tool_geometry
    assert surface._widgets["section"].width() < initial_section_width


def test_resize_preserves_the_first_visible_entry_as_scroll_anchor() -> None:
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    entries = [
        ToolboxEntry(
            title=f"Tool {index}",
            kind=constants.ENTRY_KIND_TOOL,
            path=f"/tmp/tool-{index}",
            x=constants.CANVAS_PADDING + index,
            y=constants.CANVAS_PADDING,
            entry_id=f"scroll-{index}",
        )
        for index in range(30)
    ]
    canvas = ToolboxCanvas()
    canvas.resize(500, 260)
    canvas.show()
    QtWidgets.QApplication.processEvents()
    _set_surface_entries(canvas.surface, entries, canvas.viewport().width(), True)
    canvas._sync_scrollbar_policy()
    QtWidgets.QApplication.processEvents()
    anchor_widget = canvas.surface._widgets["scroll-8"]
    canvas.verticalScrollBar().setValue(anchor_widget.y() - 11)
    anchor = canvas._capture_vertical_anchor()
    assert anchor is not None

    canvas._pending_viewport_width = 320
    canvas._apply_pending_viewport_width()

    anchored_widget = canvas.surface._widgets[anchor[0]]
    assert anchored_widget.y() - canvas.verticalScrollBar().value() == anchor[1]
    canvas.close()


def test_closing_canvas_stops_pending_resize_timer() -> None:
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    canvas = ToolboxCanvas()
    canvas._resize_layout_timer.start()
    assert canvas._resize_layout_timer.isActive()

    canvas.close()

    assert not canvas._resize_layout_timer.isActive()


def test_responsive_minimum_width_keeps_one_complete_tile_visible() -> None:
    class Owner:
        minimum_width = 0

        @staticmethod
        def minimumSizeHint() -> QtCore.QSize:
            return QtCore.QSize(159, 234)

        def setMinimumWidth(self, value: int) -> None:
            self.minimum_width = value

    class Canvas:
        @staticmethod
        def responsive_layout_enabled() -> bool:
            return True

        @staticmethod
        def tool_tile_size() -> QtCore.QSize:
            return QtCore.QSize(240, 240)

    class Context:
        canvas = Canvas()

    owner = Owner()
    update_window_minimum_width(owner, Context())  # type: ignore[arg-type]

    assert owner.minimum_width >= 240 + (2 * constants.CANVAS_PADDING)


def test_large_responsive_layout_stays_deterministic_and_fast() -> None:
    items = _items(1000)
    started = time.perf_counter()
    results = [
        build_responsive_layout(
            items,
            viewport_width=300 + (index % 20) * 25,
            tile_width=100,
            tile_height=100,
            spacing_x=10,
            spacing_y=12,
            padding=16,
            section_height=40,
            section_gap_above=8,
            section_gap_below=9,
        )
        for index in range(100)
    ]
    elapsed = time.perf_counter() - started

    assert all(len(result.rects) == 1000 for result in results)
    assert results[0] == build_responsive_layout(
        items,
        viewport_width=300,
        tile_width=100,
        tile_height=100,
        spacing_x=10,
        spacing_y=12,
        padding=16,
        section_height=40,
        section_gap_above=8,
        section_gap_below=9,
    )
    assert elapsed < 2.0
