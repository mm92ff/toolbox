import unittest

from app import constants
from app.canvas.layout_engine import CanvasLayoutEngine
from app.domain.models import ToolboxEntry


class CanvasLayoutEngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = CanvasLayoutEngine()
        self.engine.configure(
            icon_size=72,
            grid_spacing_x=28,
            grid_spacing_y=24,
            section_font_size=15,
            section_line_thickness=2,
            section_gap=12,
            section_line_color="#444a57",
        )

    def test_find_next_free_tool_position_skips_occupied_cells(self) -> None:
        cell_w, _ = self.engine.tool_cell_size()
        first_x = constants.CANVAS_PADDING
        second_x = constants.CANVAS_PADDING + cell_w
        y = constants.CANVAS_PADDING
        entries = [
            ToolboxEntry(
                title="Tool A", kind=constants.ENTRY_KIND_TOOL, path=r"C:\a.exe", x=first_x, y=y
            ),
            ToolboxEntry(
                title="Tool B", kind=constants.ENTRY_KIND_TOOL, path=r"C:\b.exe", x=second_x, y=y
            ),
        ]

        next_x, next_y = self.engine.find_next_free_tool_position(entries)

        self.assertNotIn((next_x, next_y), {(first_x, y), (second_x, y)})

    def test_snap_section_position_avoids_existing_rows(self) -> None:
        entries = [
            ToolboxEntry(
                title="Section 1",
                kind=constants.ENTRY_KIND_SECTION,
                x=constants.CANVAS_PADDING,
                y=constants.CANVAS_PADDING,
            )
        ]

        snapped = self.engine.snap_section_position(entries, constants.CANVAS_PADDING)

        self.assertNotEqual(constants.CANVAS_PADDING, snapped)

    def test_find_next_free_tool_position_avoids_section_band(self) -> None:
        entries = [
            ToolboxEntry(
                title="Header",
                kind=constants.ENTRY_KIND_SECTION,
                x=constants.CANVAS_PADDING,
                y=constants.CANVAS_PADDING,
            )
        ]

        next_x, next_y = self.engine.find_next_free_tool_position(entries)
        next_rect = self.engine.tool_rect_at(next_x, next_y)
        bands = self.engine.section_bands(entries)

        self.assertTrue(bands)
        self.assertFalse(any(next_rect.intersects(band) for band in bands))
        self.assertEqual(bands[0].bottom() + 1, next_y)

    def test_find_next_free_tool_position_stays_in_same_section_segment(self) -> None:
        first_section = ToolboxEntry(
            title="Section 1",
            kind=constants.ENTRY_KIND_SECTION,
            x=constants.CANVAS_PADDING,
            y=constants.CANVAS_PADDING,
        )
        second_section = ToolboxEntry(
            title="Section 2",
            kind=constants.ENTRY_KIND_SECTION,
            x=constants.CANVAS_PADDING,
            y=constants.CANVAS_PADDING + 400,
        )
        first_band_bottom = self.engine.section_bands([first_section])[0].bottom()
        first_row_y = first_band_bottom + 1
        entries = [
            first_section,
            second_section,
            ToolboxEntry(
                title="Tool A",
                kind=constants.ENTRY_KIND_TOOL,
                path=r"C:\a.exe",
                x=constants.CANVAS_PADDING,
                y=first_row_y,
            ),
        ]

        next_x, next_y = self.engine.find_next_free_tool_position(entries)

        self.assertEqual(first_row_y, next_y)
        self.assertGreater(next_x, constants.CANVAS_PADDING)

    def test_snap_tool_position_does_not_clamp_column_to_viewport(self) -> None:
        self.engine.set_viewport_width(300)
        cell_w, _ = self.engine.tool_cell_size()
        high_col_x = constants.CANVAS_PADDING + (4 * cell_w)
        entry = ToolboxEntry(
            title="Wide Position",
            kind=constants.ENTRY_KIND_TOOL,
            path=r"C:\wide.exe",
            x=high_col_x,
            y=constants.CANVAS_PADDING,
            entry_id="tool-wide",
        )

        snapped_x, snapped_y = self.engine.snap_tool_position(
            [entry],
            entry.x,
            entry.y,
            exclude_entry_id=entry.entry_id,
        )

        self.assertEqual(high_col_x, snapped_x)
        self.assertEqual(constants.CANVAS_PADDING, snapped_y)

    def test_insertion_row_y_targets_local_segment_row(self) -> None:
        section = ToolboxEntry(
            title="Section",
            kind=constants.ENTRY_KIND_SECTION,
            x=constants.CANVAS_PADDING,
            y=constants.CANVAS_PADDING,
        )
        bands = self.engine.section_bands([section])
        self.assertTrue(bands)
        target_y = bands[0].bottom() + 1

        insertion_y, segment_start, segment_end = self.engine.insertion_row_y(
            [section], target_y, below=False
        )

        self.assertEqual(target_y, insertion_y)
        self.assertEqual(target_y, segment_start)
        self.assertIsNone(segment_end)

    def test_insertion_row_y_uses_clicked_row_with_floor_logic(self) -> None:
        section = ToolboxEntry(
            title="Section",
            kind=constants.ENTRY_KIND_SECTION,
            x=constants.CANVAS_PADDING,
            y=constants.CANVAS_PADDING,
        )
        bands = self.engine.section_bands([section])
        self.assertTrue(bands)
        segment_start = bands[0].bottom() + 1
        row_height = self.engine.tool_cell_size()[1]
        click_y = segment_start + row_height - 1

        insertion_y, _, _ = self.engine.insertion_row_y([section], click_y, below=True)

        self.assertEqual(segment_start + row_height, insertion_y)

    def test_segment_index_for_y_changes_across_separator(self) -> None:
        section = ToolboxEntry(
            title="Section",
            kind=constants.ENTRY_KIND_SECTION,
            x=constants.CANVAS_PADDING,
            y=constants.CANVAS_PADDING + 220,
        )
        band = self.engine.section_bands([section])[0]
        idx_above = self.engine.segment_index_for_y([section], constants.CANVAS_PADDING)
        idx_below = self.engine.segment_index_for_y([section], band.bottom() + 1)

        self.assertNotEqual(idx_above, idx_below)

    def test_find_nearest_free_cell_packs_from_left(self) -> None:
        cell_w, _ = self.engine.tool_cell_size()
        y = constants.CANVAS_PADDING
        occupied = [self.engine.tool_rect_at(constants.CANVAS_PADDING, y)]

        x, result_y = self.engine.find_nearest_free_cell(
            target_col=0,
            target_y=y,
            occupied_rects=occupied,
            section_bands=[],
        )

        self.assertEqual(constants.CANVAS_PADDING + cell_w, x)
        self.assertEqual(y, result_y)


if __name__ == "__main__":
    unittest.main()
