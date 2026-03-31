import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets

from app import constants
from app.canvas.layout_engine import CanvasLayoutEngine
from app.canvas.toolbox_canvas import CanvasSurface
from app.domain.models import ToolboxEntry


class CanvasSurfaceMultiselectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def _tool_cell_size(self) -> tuple[int, int]:
        engine = CanvasLayoutEngine()
        engine.configure(
            icon_size=constants.DEFAULT_ICON_SIZE,
            grid_spacing_x=constants.DEFAULT_GRID_SPACING_X,
            grid_spacing_y=constants.DEFAULT_GRID_SPACING_Y,
            section_font_size=constants.DEFAULT_SECTION_FONT_SIZE,
            section_line_thickness=constants.DEFAULT_SECTION_LINE_THICKNESS,
            section_gap=constants.DEFAULT_SECTION_PROTECTED_GAP,
            section_line_color=constants.DEFAULT_SECTION_LINE_COLOR,
        )
        return engine.tool_cell_size()

    def _create_surface_with_two_tools(self) -> tuple[CanvasSurface, list[ToolboxEntry]]:
        cell_w, _ = self._tool_cell_size()
        y = constants.CANVAS_PADDING
        entries = [
            ToolboxEntry(
                title="A",
                kind=constants.ENTRY_KIND_TOOL,
                path=r"C:\a.exe",
                x=constants.CANVAS_PADDING,
                y=y,
                entry_id="tool-a",
            ),
            ToolboxEntry(
                title="B",
                kind=constants.ENTRY_KIND_TOOL,
                path=r"C:\b.exe",
                x=constants.CANVAS_PADDING + cell_w,
                y=y,
                entry_id="tool-b",
            ),
        ]
        surface = CanvasSurface()
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
            hidden_entry_ids=set(),
            viewport_width=1200,
        )
        surface.show()
        QtWidgets.QApplication.processEvents()
        return surface, entries

    def _create_surface_with_section_and_two_tools(
        self,
    ) -> tuple[CanvasSurface, list[ToolboxEntry]]:
        cell_w, _ = self._tool_cell_size()
        entries = [
            ToolboxEntry(
                title="Header",
                kind=constants.ENTRY_KIND_SECTION,
                x=constants.CANVAS_PADDING,
                y=constants.CANVAS_PADDING,
                entry_id="section-1",
            ),
            ToolboxEntry(
                title="A",
                kind=constants.ENTRY_KIND_TOOL,
                path=r"C:\a.exe",
                x=constants.CANVAS_PADDING,
                y=constants.CANVAS_PADDING + 102,
                entry_id="tool-a",
            ),
            ToolboxEntry(
                title="B",
                kind=constants.ENTRY_KIND_TOOL,
                path=r"C:\b.exe",
                x=constants.CANVAS_PADDING + cell_w,
                y=constants.CANVAS_PADDING + 102,
                entry_id="tool-b",
            ),
        ]
        surface = CanvasSurface()
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
            hidden_entry_ids=set(),
            viewport_width=1200,
        )
        surface.show()
        QtWidgets.QApplication.processEvents()
        return surface, entries

    def test_entry_ids_in_selection_rect_finds_visible_items(self) -> None:
        surface, _entries = self._create_surface_with_two_tools()
        cell_w, _ = self._tool_cell_size()
        selection_rect = QtCore.QRect(
            constants.CANVAS_PADDING - 2, constants.CANVAS_PADDING - 2, (3 * cell_w), 320
        )

        selected = surface._entry_ids_in_selection_rect(selection_rect)

        self.assertIn("tool-a", selected)
        self.assertIn("tool-b", selected)

    def test_group_move_live_and_finish_moves_selected_tools_together(self) -> None:
        surface, entries = self._create_surface_with_two_tools()
        cell_w, cell_h = self._tool_cell_size()
        surface.select_entries({"tool-a", "tool-b"})

        widget_a = surface._widgets["tool-a"]
        widget_b = surface._widgets["tool-b"]
        original_b = (widget_b.x(), widget_b.y())
        target_a = (widget_a.x() + cell_w, widget_a.y() + cell_h)
        widget_a.move(*target_a)

        surface._on_widget_move_live("tool-a")
        self.assertEqual(
            (original_b[0] + cell_w, original_b[1] + cell_h), (widget_b.x(), widget_b.y())
        )

        surface._on_widget_move_finished("tool-a", widget_a.x(), widget_a.y())

        moved_a = next(item for item in entries if item.entry_id == "tool-a")
        moved_b = next(item for item in entries if item.entry_id == "tool-b")
        self.assertEqual(target_a, (moved_a.x, moved_a.y))
        self.assertEqual((original_b[0] + cell_w, original_b[1] + cell_h), (moved_b.x, moved_b.y))

    def test_group_move_finish_preserves_selected_tool_structure(self) -> None:
        surface, entries = self._create_surface_with_two_tools()
        cell_w, cell_h = self._tool_cell_size()
        surface.select_entries({"tool-a", "tool-b"})
        widget_a = surface._widgets["tool-a"]

        tool_a = next(item for item in entries if item.entry_id == "tool-a")
        tool_b = next(item for item in entries if item.entry_id == "tool-b")
        initial_dx = tool_b.x - tool_a.x
        initial_dy = tool_b.y - tool_a.y

        widget_a.move(widget_a.x() + (2 * cell_w), widget_a.y() + (2 * cell_h))
        surface._on_widget_move_live("tool-a")
        surface._on_widget_move_finished("tool-a", widget_a.x(), widget_a.y())

        self.assertEqual(initial_dx, tool_b.x - tool_a.x)
        self.assertEqual(initial_dy, tool_b.y - tool_a.y)

    def test_mixed_group_live_move_does_not_jump_section_to_far_safe_y(self) -> None:
        surface, _entries = self._create_surface_with_section_and_two_tools()
        surface.select_entries({"section-1", "tool-a", "tool-b"})
        section_widget = surface._widgets["section-1"]
        tool_a_widget = surface._widgets["tool-a"]
        tool_b_widget = surface._widgets["tool-b"]
        original_a_x = tool_a_widget.x()
        original_b_x = tool_b_widget.x()

        section_widget.move(constants.CANVAS_PADDING + 20, constants.CANVAS_PADDING + 40)
        section_widget.move_live.emit()

        self.assertEqual(constants.CANVAS_PADDING, section_widget.x())
        self.assertEqual(constants.CANVAS_PADDING + 40, section_widget.y())
        self.assertEqual(original_a_x, tool_a_widget.x())
        self.assertEqual(original_b_x, tool_b_widget.x())

    def test_mixed_group_live_move_applies_section_drop_hint_when_tool_is_leader(self) -> None:
        surface, _entries = self._create_surface_with_section_and_two_tools()
        surface.select_entries({"section-1", "tool-a"})
        section_widget = surface._widgets["section-1"]
        tool_widget = surface._widgets["tool-a"]

        surface._section_drop_intersects_tools = lambda *_args, **_kwargs: True

        tool_widget.move(tool_widget.x(), tool_widget.y() + 40)
        surface._on_widget_move_live("tool-a")

        self.assertTrue(bool(section_widget.property("drop_hint")))
        self.assertEqual("conflict", section_widget.property("drop_hint_state"))

    def test_mixed_group_finish_keeps_selected_tools_near_translated_position(self) -> None:
        surface, entries = self._create_surface_with_section_and_two_tools()
        surface.select_entries({"section-1", "tool-a", "tool-b"})
        section_widget = surface._widgets["section-1"]
        tool_a = next(item for item in entries if item.entry_id == "tool-a")
        tool_b = next(item for item in entries if item.entry_id == "tool-b")
        original_a = (tool_a.x, tool_a.y)
        original_b = (tool_b.x, tool_b.y)

        section_widget.move(constants.CANVAS_PADDING + 20, constants.CANVAS_PADDING + 40)
        section_widget.move_live.emit()
        section_widget.move_finished.emit("section-1", section_widget.x(), section_widget.y())

        self.assertEqual(original_a[0], tool_a.x)
        self.assertEqual(original_b[0], tool_b.x)
        delta_a = tool_a.y - original_a[1]
        delta_b = tool_b.y - original_b[1]
        self.assertGreaterEqual(delta_a, 40)
        self.assertGreaterEqual(delta_b, 40)
        self.assertEqual(delta_a, delta_b)

    def test_mixed_group_finish_does_not_stack_on_unselected_tool(self) -> None:
        surface, entries = self._create_surface_with_section_and_two_tools()
        cell_w, _ = self._tool_cell_size()
        entries.append(
            ToolboxEntry(
                title="Unselected",
                kind=constants.ENTRY_KIND_TOOL,
                path=r"C:\u.exe",
                x=constants.CANVAS_PADDING + cell_w,
                y=constants.CANVAS_PADDING + 106,
                entry_id="tool-u",
            )
        )
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
            hidden_entry_ids=set(),
            viewport_width=1200,
        )
        surface.show()
        QtWidgets.QApplication.processEvents()
        surface.select_entries({"section-1", "tool-a", "tool-b"})
        section_widget = surface._widgets["section-1"]

        section_widget.move(constants.CANVAS_PADDING + 20, constants.CANVAS_PADDING + 40)
        section_widget.move_live.emit()
        section_widget.move_finished.emit("section-1", section_widget.x(), section_widget.y())

        engine = surface._layout_engine
        tools = [entry for entry in entries if entry.is_tool]
        for index, first in enumerate(tools):
            first_rect = engine.tool_rect_at(first.x, first.y)
            for second in tools[index + 1 :]:
                second_rect = engine.tool_rect_at(second.x, second.y)
                self.assertFalse(first_rect.intersects(second_rect))

    def test_mixed_group_finish_keeps_gap_close_to_live_gap(self) -> None:
        entries = [
            ToolboxEntry(
                title="Top Header",
                kind=constants.ENTRY_KIND_SECTION,
                x=constants.CANVAS_PADDING,
                y=constants.CANVAS_PADDING,
                entry_id="section-top",
            ),
            ToolboxEntry(
                title="Moved Header",
                kind=constants.ENTRY_KIND_SECTION,
                x=constants.CANVAS_PADDING,
                y=220,
                entry_id="section-moved",
            ),
            ToolboxEntry(
                title="A",
                kind=constants.ENTRY_KIND_TOOL,
                path=r"C:\a.exe",
                x=constants.CANVAS_PADDING,
                y=300,
                entry_id="tool-a",
            ),
            ToolboxEntry(
                title="B",
                kind=constants.ENTRY_KIND_TOOL,
                path=r"C:\b.exe",
                x=180,
                y=300,
                entry_id="tool-b",
            ),
            ToolboxEntry(
                title="C",
                kind=constants.ENTRY_KIND_TOOL,
                path=r"C:\c.exe",
                x=342,
                y=300,
                entry_id="tool-c",
            ),
        ]
        surface = CanvasSurface()
        surface.set_entries(
            entries=entries,
            icon_provider=QtWidgets.QFileIconProvider(),
            icon_size=constants.DEFAULT_ICON_SIZE,
            tile_frame_enabled=constants.DEFAULT_TILE_FRAME_ENABLED,
            tile_frame_thickness=constants.DEFAULT_TILE_FRAME_THICKNESS,
            tile_frame_color=constants.DEFAULT_TILE_FRAME_COLOR,
            tile_highlight_color=constants.DEFAULT_TILE_HIGHLIGHT_COLOR,
            grid_spacing_x=0,
            grid_spacing_y=0,
            auto_compact_left=constants.DEFAULT_AUTO_COMPACT_LEFT,
            section_font_size=12,
            section_line_thickness=3,
            section_gap=10,
            section_line_color=constants.DEFAULT_SECTION_LINE_COLOR,
            selected_entry_ids=set(),
            hidden_entry_ids=set(),
            viewport_width=1200,
        )
        surface.show()
        QtWidgets.QApplication.processEvents()
        surface.select_entries({"section-moved", "tool-a", "tool-b", "tool-c"})

        section_widget = surface._widgets["section-moved"]
        tool_a_widget = surface._widgets["tool-a"]
        section_widget.move(section_widget.x(), section_widget.y() - 110)
        section_widget.move_live.emit()
        live_gap = tool_a_widget.y() - section_widget.y()

        section_widget.move_finished.emit("section-moved", section_widget.x(), section_widget.y())
        section_entry = next(item for item in entries if item.entry_id == "section-moved")
        tool_a_entry = next(item for item in entries if item.entry_id == "tool-a")
        final_gap = tool_a_entry.y - section_entry.y

        self.assertEqual(final_gap, live_gap)


if __name__ == "__main__":
    unittest.main()
