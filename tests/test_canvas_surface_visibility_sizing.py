import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets

from app import constants
from app.canvas.layout_engine import CanvasLayoutEngine
from app.canvas.toolbox_canvas import CanvasSurface
from app.domain.models import ToolboxEntry


class CanvasSurfaceVisibilitySizingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_update_canvas_size_uses_entry_geometry_when_surface_hidden(self) -> None:
        icon_size = constants.DEFAULT_ICON_SIZE
        grid_x = constants.DEFAULT_GRID_SPACING_X
        grid_y = constants.DEFAULT_GRID_SPACING_Y
        engine = CanvasLayoutEngine()
        engine.configure(
            icon_size=icon_size,
            grid_spacing_x=grid_x,
            grid_spacing_y=grid_y,
            section_font_size=constants.DEFAULT_SECTION_FONT_SIZE,
            section_line_thickness=constants.DEFAULT_SECTION_LINE_THICKNESS,
            section_gap=constants.DEFAULT_SECTION_PROTECTED_GAP,
            section_line_color=constants.DEFAULT_SECTION_LINE_COLOR,
        )
        deep_tool_y = 900
        entries = [
            ToolboxEntry(
                title="A",
                kind=constants.ENTRY_KIND_TOOL,
                path=r"C:\a.exe",
                x=constants.CANVAS_PADDING,
                y=deep_tool_y,
                entry_id="tool-a",
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
        surface.hide()
        QtWidgets.QApplication.processEvents()

        changed = surface.apply_layout_settings(
            entries=entries,
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
        )

        expected_min_height = (
            engine.tool_rect_at(constants.CANVAS_PADDING, deep_tool_y).bottom()
            + constants.CANVAS_PADDING
        )
        self.assertFalse(changed)
        self.assertGreaterEqual(surface.height(), expected_min_height)


if __name__ == "__main__":
    unittest.main()
