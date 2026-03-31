import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets

from app import constants
from app.canvas.layout_engine import CanvasLayoutEngine
from app.canvas.toolbox_canvas import CanvasSurface
from app.domain.models import ToolboxEntry


class CanvasSurfaceSectionGapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def _engine(self, section_gap: int) -> CanvasLayoutEngine:
        engine = CanvasLayoutEngine()
        engine.configure(
            icon_size=constants.DEFAULT_ICON_SIZE,
            grid_spacing_x=constants.DEFAULT_GRID_SPACING_X,
            grid_spacing_y=constants.DEFAULT_GRID_SPACING_Y,
            section_font_size=constants.DEFAULT_SECTION_FONT_SIZE,
            section_line_thickness=constants.DEFAULT_SECTION_LINE_THICKNESS,
            section_gap=section_gap,
            section_line_color=constants.DEFAULT_SECTION_LINE_COLOR,
        )
        engine.set_viewport_width(1200)
        return engine

    def test_apply_layout_settings_reflows_tools_for_larger_section_gap(self) -> None:
        old_gap = constants.DEFAULT_SECTION_PROTECTED_GAP
        new_gap = old_gap + 50
        old_engine = self._engine(old_gap)
        old_band = old_engine.section_protected_rect_at(constants.CANVAS_PADDING)
        tool_y = old_band.bottom() + 1
        entries = [
            ToolboxEntry(
                title="Header",
                kind=constants.ENTRY_KIND_SECTION,
                x=constants.CANVAS_PADDING,
                y=constants.CANVAS_PADDING,
                entry_id="section-1",
            ),
            ToolboxEntry(
                title="Tool",
                kind=constants.ENTRY_KIND_TOOL,
                path=r"C:\tool.exe",
                x=constants.CANVAS_PADDING,
                y=tool_y,
                entry_id="tool-1",
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
            section_gap=old_gap,
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
            grid_spacing_x=constants.DEFAULT_GRID_SPACING_X,
            grid_spacing_y=constants.DEFAULT_GRID_SPACING_Y,
            auto_compact_left=constants.DEFAULT_AUTO_COMPACT_LEFT,
            section_font_size=constants.DEFAULT_SECTION_FONT_SIZE,
            section_line_thickness=constants.DEFAULT_SECTION_LINE_THICKNESS,
            section_gap=new_gap,
            section_line_color=constants.DEFAULT_SECTION_LINE_COLOR,
        )

        moved_tool = next(item for item in entries if item.entry_id == "tool-1")
        new_engine = self._engine(new_gap)
        new_band = new_engine.section_protected_rect_at(constants.CANVAS_PADDING)
        moved_tool_rect = new_engine.tool_rect_at(moved_tool.x, moved_tool.y)

        self.assertTrue(changed)
        self.assertFalse(moved_tool_rect.intersects(new_band))

    def test_apply_layout_settings_shifts_tools_even_without_initial_collision(self) -> None:
        old_gap = constants.DEFAULT_SECTION_PROTECTED_GAP
        new_gap = old_gap + 16
        old_engine = self._engine(old_gap)
        old_band = old_engine.section_protected_rect_at(constants.CANVAS_PADDING)
        tool_y = old_band.bottom() + 80
        entries = [
            ToolboxEntry(
                title="Header",
                kind=constants.ENTRY_KIND_SECTION,
                x=constants.CANVAS_PADDING,
                y=constants.CANVAS_PADDING,
                entry_id="section-1",
            ),
            ToolboxEntry(
                title="Tool",
                kind=constants.ENTRY_KIND_TOOL,
                path=r"C:\tool.exe",
                x=constants.CANVAS_PADDING,
                y=tool_y,
                entry_id="tool-1",
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
            section_gap=old_gap,
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
            grid_spacing_x=constants.DEFAULT_GRID_SPACING_X,
            grid_spacing_y=constants.DEFAULT_GRID_SPACING_Y,
            auto_compact_left=constants.DEFAULT_AUTO_COMPACT_LEFT,
            section_font_size=constants.DEFAULT_SECTION_FONT_SIZE,
            section_line_thickness=constants.DEFAULT_SECTION_LINE_THICKNESS,
            section_gap=new_gap,
            section_line_color=constants.DEFAULT_SECTION_LINE_COLOR,
        )

        moved_tool = next(item for item in entries if item.entry_id == "tool-1")
        new_engine = self._engine(new_gap)
        new_band = new_engine.section_protected_rect_at(constants.CANVAS_PADDING)
        expected_shift = new_band.bottom() - old_band.bottom()

        self.assertTrue(changed)
        self.assertEqual(moved_tool.y, tool_y + expected_shift)


if __name__ == "__main__":
    unittest.main()
