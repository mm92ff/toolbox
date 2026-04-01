import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets

from app import constants
from app.canvas.layout_engine import CanvasLayoutEngine
from app.canvas.toolbox_canvas import CanvasSurface
from app.domain.models import ToolboxEntry


class CanvasSurfaceLayoutReflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    @staticmethod
    def _tool_cell_size(icon_size: int, grid_spacing_x: int, grid_spacing_y: int) -> tuple[int, int]:
        engine = CanvasLayoutEngine()
        engine.configure(
            icon_size=icon_size,
            grid_spacing_x=grid_spacing_x,
            grid_spacing_y=grid_spacing_y,
            section_font_size=constants.DEFAULT_SECTION_FONT_SIZE,
            section_line_thickness=constants.DEFAULT_SECTION_LINE_THICKNESS,
            section_gap=constants.DEFAULT_SECTION_PROTECTED_GAP,
            section_line_color=constants.DEFAULT_SECTION_LINE_COLOR,
        )
        return engine.tool_cell_size()

    def test_apply_layout_settings_reflows_tool_grid_for_icon_size_change(self) -> None:
        old_icon_size = constants.DEFAULT_ICON_SIZE
        new_icon_size = min(constants.MAX_ICON_SIZE, old_icon_size + 24)
        old_cell_w, old_cell_h = self._tool_cell_size(
            old_icon_size,
            constants.DEFAULT_GRID_SPACING_X,
            constants.DEFAULT_GRID_SPACING_Y,
        )
        entries = [
            ToolboxEntry(
                title="A",
                kind=constants.ENTRY_KIND_TOOL,
                path=r"C:\a.exe",
                x=constants.CANVAS_PADDING,
                y=constants.CANVAS_PADDING,
                entry_id="tool-a",
            ),
            ToolboxEntry(
                title="B",
                kind=constants.ENTRY_KIND_TOOL,
                path=r"C:\b.exe",
                x=constants.CANVAS_PADDING + old_cell_w,
                y=constants.CANVAS_PADDING,
                entry_id="tool-b",
            ),
            ToolboxEntry(
                title="C",
                kind=constants.ENTRY_KIND_TOOL,
                path=r"C:\c.exe",
                x=constants.CANVAS_PADDING + (2 * old_cell_w),
                y=constants.CANVAS_PADDING + old_cell_h,
                entry_id="tool-c",
            ),
        ]
        surface = CanvasSurface()
        surface.set_entries(
            entries=entries,
            icon_provider=QtWidgets.QFileIconProvider(),
            icon_size=old_icon_size,
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

        changed = surface.apply_layout_settings(
            entries=entries,
            icon_size=new_icon_size,
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
        )

        new_cell_w, new_cell_h = self._tool_cell_size(
            new_icon_size,
            constants.DEFAULT_GRID_SPACING_X,
            constants.DEFAULT_GRID_SPACING_Y,
        )
        tool_a = next(item for item in entries if item.entry_id == "tool-a")
        tool_b = next(item for item in entries if item.entry_id == "tool-b")
        tool_c = next(item for item in entries if item.entry_id == "tool-c")

        self.assertTrue(changed)
        self.assertEqual((constants.CANVAS_PADDING, constants.CANVAS_PADDING), (tool_a.x, tool_a.y))
        self.assertEqual((constants.CANVAS_PADDING + new_cell_w, constants.CANVAS_PADDING), (tool_b.x, tool_b.y))
        self.assertEqual(
            (constants.CANVAS_PADDING + (2 * new_cell_w), constants.CANVAS_PADDING + new_cell_h),
            (tool_c.x, tool_c.y),
        )

    def test_apply_layout_settings_reflows_tool_grid_for_grid_spacing_change(self) -> None:
        old_grid_x = constants.DEFAULT_GRID_SPACING_X
        old_grid_y = constants.DEFAULT_GRID_SPACING_Y
        new_grid_x = min(constants.MAX_GRID_SPACING, old_grid_x + 40)
        new_grid_y = min(constants.MAX_GRID_SPACING, old_grid_y + 20)
        old_cell_w, old_cell_h = self._tool_cell_size(
            constants.DEFAULT_ICON_SIZE,
            old_grid_x,
            old_grid_y,
        )
        entries = [
            ToolboxEntry(
                title="A",
                kind=constants.ENTRY_KIND_TOOL,
                path=r"C:\a.exe",
                x=constants.CANVAS_PADDING,
                y=constants.CANVAS_PADDING + old_cell_h,
                entry_id="tool-a",
            ),
            ToolboxEntry(
                title="B",
                kind=constants.ENTRY_KIND_TOOL,
                path=r"C:\b.exe",
                x=constants.CANVAS_PADDING + (3 * old_cell_w),
                y=constants.CANVAS_PADDING + (2 * old_cell_h),
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
            grid_spacing_x=old_grid_x,
            grid_spacing_y=old_grid_y,
            auto_compact_left=constants.DEFAULT_AUTO_COMPACT_LEFT,
            section_font_size=constants.DEFAULT_SECTION_FONT_SIZE,
            section_line_thickness=constants.DEFAULT_SECTION_LINE_THICKNESS,
            section_gap=constants.DEFAULT_SECTION_PROTECTED_GAP,
            section_line_color=constants.DEFAULT_SECTION_LINE_COLOR,
            selected_entry_ids=set(),
            hidden_entry_ids=set(),
            viewport_width=1200,
        )

        changed = surface.apply_layout_settings(
            entries=entries,
            icon_size=constants.DEFAULT_ICON_SIZE,
            tile_frame_enabled=constants.DEFAULT_TILE_FRAME_ENABLED,
            tile_frame_thickness=constants.DEFAULT_TILE_FRAME_THICKNESS,
            tile_frame_color=constants.DEFAULT_TILE_FRAME_COLOR,
            tile_highlight_color=constants.DEFAULT_TILE_HIGHLIGHT_COLOR,
            grid_spacing_x=new_grid_x,
            grid_spacing_y=new_grid_y,
            auto_compact_left=constants.DEFAULT_AUTO_COMPACT_LEFT,
            section_font_size=constants.DEFAULT_SECTION_FONT_SIZE,
            section_line_thickness=constants.DEFAULT_SECTION_LINE_THICKNESS,
            section_gap=constants.DEFAULT_SECTION_PROTECTED_GAP,
            section_line_color=constants.DEFAULT_SECTION_LINE_COLOR,
        )

        new_cell_w, new_cell_h = self._tool_cell_size(
            constants.DEFAULT_ICON_SIZE,
            new_grid_x,
            new_grid_y,
        )
        tool_a = next(item for item in entries if item.entry_id == "tool-a")
        tool_b = next(item for item in entries if item.entry_id == "tool-b")

        self.assertTrue(changed)
        self.assertEqual((constants.CANVAS_PADDING, constants.CANVAS_PADDING + new_cell_h), (tool_a.x, tool_a.y))
        self.assertEqual(
            (constants.CANVAS_PADDING + (3 * new_cell_w), constants.CANVAS_PADDING + (2 * new_cell_h)),
            (tool_b.x, tool_b.y),
        )

    def test_apply_layout_settings_keeps_segment_local_rows_with_sections(self) -> None:
        old_icon_size = constants.DEFAULT_ICON_SIZE
        new_icon_size = min(constants.MAX_ICON_SIZE, old_icon_size + 48)
        old_cell_w, old_cell_h = self._tool_cell_size(
            old_icon_size,
            constants.DEFAULT_GRID_SPACING_X,
            constants.DEFAULT_GRID_SPACING_Y,
        )
        old_engine = CanvasLayoutEngine()
        old_engine.configure(
            icon_size=old_icon_size,
            grid_spacing_x=constants.DEFAULT_GRID_SPACING_X,
            grid_spacing_y=constants.DEFAULT_GRID_SPACING_Y,
            section_font_size=constants.DEFAULT_SECTION_FONT_SIZE,
            section_line_thickness=constants.DEFAULT_SECTION_LINE_THICKNESS,
            section_gap=constants.DEFAULT_SECTION_PROTECTED_GAP,
            section_line_color=constants.DEFAULT_SECTION_LINE_COLOR,
        )
        old_engine.set_viewport_width(1200)
        section_entries = [
            ToolboxEntry(
                title="S1",
                kind=constants.ENTRY_KIND_SECTION,
                x=constants.CANVAS_PADDING,
                y=constants.CANVAS_PADDING,
                entry_id="section-1",
            ),
            ToolboxEntry(
                title="S2",
                kind=constants.ENTRY_KIND_SECTION,
                x=constants.CANVAS_PADDING,
                y=constants.CANVAS_PADDING + 180,
                entry_id="section-2",
            ),
        ]
        old_segments = old_engine.segment_ranges(section_entries)
        second_segment_start = old_segments[2][0]
        entries = [
            *section_entries,
            ToolboxEntry(
                title="A",
                kind=constants.ENTRY_KIND_TOOL,
                path=r"C:\a.exe",
                x=constants.CANVAS_PADDING,
                y=second_segment_start,
                entry_id="tool-a",
            ),
            ToolboxEntry(
                title="B",
                kind=constants.ENTRY_KIND_TOOL,
                path=r"C:\b.exe",
                x=constants.CANVAS_PADDING + old_cell_w,
                y=second_segment_start + old_cell_h,
                entry_id="tool-b",
            ),
        ]
        surface = CanvasSurface()
        surface.set_entries(
            entries=entries,
            icon_provider=QtWidgets.QFileIconProvider(),
            icon_size=old_icon_size,
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

        changed = surface.apply_layout_settings(
            entries=entries,
            icon_size=new_icon_size,
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
        )

        new_cell_w, new_cell_h = self._tool_cell_size(
            new_icon_size,
            constants.DEFAULT_GRID_SPACING_X,
            constants.DEFAULT_GRID_SPACING_Y,
        )
        new_engine = CanvasLayoutEngine()
        new_engine.configure(
            icon_size=new_icon_size,
            grid_spacing_x=constants.DEFAULT_GRID_SPACING_X,
            grid_spacing_y=constants.DEFAULT_GRID_SPACING_Y,
            section_font_size=constants.DEFAULT_SECTION_FONT_SIZE,
            section_line_thickness=constants.DEFAULT_SECTION_LINE_THICKNESS,
            section_gap=constants.DEFAULT_SECTION_PROTECTED_GAP,
            section_line_color=constants.DEFAULT_SECTION_LINE_COLOR,
        )
        new_engine.set_viewport_width(1200)
        new_second_segment_start = new_engine.segment_ranges(entries)[2][0]
        tool_a = next(item for item in entries if item.entry_id == "tool-a")
        tool_b = next(item for item in entries if item.entry_id == "tool-b")

        self.assertTrue(changed)
        self.assertEqual(
            (constants.CANVAS_PADDING, new_second_segment_start),
            (tool_a.x, tool_a.y),
        )
        self.assertEqual(
            (constants.CANVAS_PADDING + new_cell_w, new_second_segment_start + new_cell_h),
            (tool_b.x, tool_b.y),
        )

    def test_set_entries_normalizes_overlapping_imported_tool_positions(self) -> None:
        """Imported legacy coordinates should be remapped to non-overlapping tool cells."""
        icon_size = 79
        grid_x = 0
        grid_y = 0
        entries = [
            ToolboxEntry(
                title="A",
                kind=constants.ENTRY_KIND_TOOL,
                path=r"C:\a.exe",
                x=constants.CANVAS_PADDING,
                y=constants.CANVAS_PADDING,
                entry_id="tool-a",
            ),
            ToolboxEntry(
                title="B",
                kind=constants.ENTRY_KIND_TOOL,
                path=r"C:\b.exe",
                x=constants.CANVAS_PADDING + 120,
                y=constants.CANVAS_PADDING,
                entry_id="tool-b",
            ),
            ToolboxEntry(
                title="C",
                kind=constants.ENTRY_KIND_TOOL,
                path=r"C:\c.exe",
                x=constants.CANVAS_PADDING + 240,
                y=constants.CANVAS_PADDING,
                entry_id="tool-c",
            ),
            ToolboxEntry(
                title="D",
                kind=constants.ENTRY_KIND_TOOL,
                path=r"C:\d.exe",
                x=constants.CANVAS_PADDING + 120,
                y=constants.CANVAS_PADDING + 102,
                entry_id="tool-d",
            ),
        ]
        surface = CanvasSurface()
        surface.set_entries(
            entries=entries,
            icon_provider=QtWidgets.QFileIconProvider(),
            icon_size=icon_size,
            tile_frame_enabled=constants.DEFAULT_TILE_FRAME_ENABLED,
            tile_frame_thickness=constants.DEFAULT_TILE_FRAME_THICKNESS,
            tile_frame_color=constants.DEFAULT_TILE_FRAME_COLOR,
            tile_highlight_color=constants.DEFAULT_TILE_HIGHLIGHT_COLOR,
            grid_spacing_x=grid_x,
            grid_spacing_y=grid_y,
            auto_compact_left=constants.DEFAULT_AUTO_COMPACT_LEFT,
            section_font_size=constants.DEFAULT_SECTION_FONT_SIZE,
            section_line_thickness=constants.DEFAULT_SECTION_LINE_THICKNESS,
            section_gap=constants.DEFAULT_SECTION_PROTECTED_GAP,
            section_line_color=constants.DEFAULT_SECTION_LINE_COLOR,
            selected_entry_ids=set(),
            hidden_entry_ids=set(),
            viewport_width=1200,
        )

        rects: list[tuple[str, object]] = []
        for entry in entries:
            rect = surface._layout_engine.tool_rect_at(entry.x, entry.y)
            for other_id, other_rect in rects:
                self.assertFalse(
                    rect.intersects(other_rect),
                    msg=f"Entries overlap after restore normalization: {other_id} vs {entry.entry_id}",
                )
            rects.append((entry.entry_id, rect))


if __name__ == "__main__":
    unittest.main()
