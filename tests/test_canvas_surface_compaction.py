import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets

from app import constants
from app.canvas.layout_engine import CanvasLayoutEngine
from app.canvas.toolbox_canvas import CanvasSurface
from app.domain.models import ToolboxEntry


class CanvasSurfaceCompactionToggleTests(unittest.TestCase):
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

    def _create_surface_with_gap(
        self, auto_compact_left: bool
    ) -> tuple[CanvasSurface, list[ToolboxEntry]]:
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
                x=constants.CANVAS_PADDING + (2 * cell_w),
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
            auto_compact_left=auto_compact_left,
            section_font_size=constants.DEFAULT_SECTION_FONT_SIZE,
            section_line_thickness=constants.DEFAULT_SECTION_LINE_THICKNESS,
            section_gap=constants.DEFAULT_SECTION_PROTECTED_GAP,
            section_line_color=constants.DEFAULT_SECTION_LINE_COLOR,
            selected_entry_ids=set(),
            hidden_entry_ids=set(),
            viewport_width=1200,
        )
        return surface, entries

    def test_move_keeps_gap_when_auto_compact_disabled(self) -> None:
        surface, entries = self._create_surface_with_gap(auto_compact_left=False)
        original_x = entries[1].x

        surface._on_widget_move_finished("tool-b", entries[1].x, entries[1].y)

        self.assertEqual(original_x, entries[1].x)

    def test_move_closes_gap_when_auto_compact_enabled(self) -> None:
        surface, entries = self._create_surface_with_gap(auto_compact_left=True)
        cell_w, _ = self._tool_cell_size()

        surface._on_widget_move_finished("tool-b", entries[1].x, entries[1].y)

        self.assertEqual(constants.CANVAS_PADDING + cell_w, entries[1].x)


if __name__ == "__main__":
    unittest.main()
