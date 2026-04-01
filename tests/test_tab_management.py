import os
import shutil
import unittest
import uuid
import weakref

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtGui, QtWidgets

from app import constants
from app.main_window import MainWindow
from app.ui.widgets.input_controls import NoWheelSlider


class TabManagementTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def _create_window(self) -> MainWindow:
        app_name = f"ToolboxStarter_TestTabs_{uuid.uuid4().hex}"
        return MainWindow(app_name)

    def test_toolbox_context_lookup_uses_visible_widget_mapping(self) -> None:
        window = self._create_window()
        try:
            first = window.toolbox_tabs[0]
            second = window._create_toolbox_tab("Second", entries=[], is_primary=False)
            window._hidden_toolbox_tab_ids = {first.tab_id}
            window._reinsert_fixed_tabs(preferred_widget=second.page)

            resolved = window._toolbox_context_for_index(0)

            self.assertIs(second, resolved)
        finally:
            config_dir = window.config_dir
            window.close()
            shutil.rmtree(config_dir, ignore_errors=True)

    def test_tab_manager_move_button_reorders_toolbox_tabs_after_apply(self) -> None:
        window = self._create_window()
        try:
            first = window.toolbox_tabs[0]
            second = window._create_toolbox_tab("Second", entries=[], is_primary=False)
            tab_list: QtWidgets.QListWidget = window.widgets[constants.WIDGET_TAB_MANAGER_LIST]  # type: ignore[assignment]
            second_key = window._tab_manager_key_for_toolbox(second.tab_id)

            selected_row = -1
            for row in range(tab_list.count()):
                item = tab_list.item(row)
                if str(item.data(window._TAB_KEY_ROLE) or "") == second_key:
                    selected_row = row
                    break
            self.assertGreaterEqual(selected_row, 0)

            tab_list.setCurrentRow(selected_row)
            window._move_selected_tab_in_manager(-1)

            self.assertEqual(first.tab_id, window.toolbox_tabs[0].tab_id)
            self.assertEqual(second.tab_id, window.toolbox_tabs[1].tab_id)
            self.assertTrue(window._settings_dirty)

            window._apply_pending_settings()

            self.assertEqual(second.tab_id, window.toolbox_tabs[0].tab_id)
            self.assertEqual(first.tab_id, window.toolbox_tabs[1].tab_id)
            self.assertFalse(window._settings_dirty)
        finally:
            config_dir = window.config_dir
            window.close()
            shutil.rmtree(config_dir, ignore_errors=True)

    def test_drop_widget_map_uses_weak_references(self) -> None:
        window = self._create_window()
        try:
            self.assertIsInstance(window._drop_widget_map, weakref.WeakKeyDictionary)
        finally:
            config_dir = window.config_dir
            window.close()
            shutil.rmtree(config_dir, ignore_errors=True)

    def test_leaving_settings_tab_auto_applies_dirty_layout_changes(self) -> None:
        window = self._create_window()
        try:
            settings_index = window.tab_widget.indexOf(window.settings_tab)
            toolbox_index = window.tab_widget.indexOf(window.toolbox_tabs[0].page)
            self.assertGreaterEqual(settings_index, 0)
            self.assertGreaterEqual(toolbox_index, 0)

            window.tab_widget.setCurrentIndex(settings_index)
            QtWidgets.QApplication.processEvents()

            icon_slider: QtWidgets.QSlider = window.widgets[constants.WIDGET_ICON_SIZE_SLIDER]  # type: ignore[assignment]
            old_icon_size = window.current_icon_size()
            new_icon_size = min(icon_slider.maximum(), old_icon_size + 7)
            if new_icon_size == old_icon_size:
                new_icon_size = max(icon_slider.minimum(), old_icon_size - 7)
            self.assertNotEqual(old_icon_size, new_icon_size)

            icon_slider.setValue(new_icon_size)
            QtWidgets.QApplication.processEvents()
            self.assertTrue(window._settings_dirty)

            window.tab_widget.setCurrentIndex(toolbox_index)
            QtWidgets.QApplication.processEvents()

            self.assertFalse(window._settings_dirty)
            self.assertEqual(new_icon_size, window.current_icon_size())
        finally:
            config_dir = window.config_dir
            window.close()
            shutil.rmtree(config_dir, ignore_errors=True)

    def test_icon_size_live_preview_updates_when_slider_changes(self) -> None:
        window = self._create_window()
        try:
            settings_index = window.tab_widget.indexOf(window.settings_tab)
            self.assertGreaterEqual(settings_index, 0)
            window.tab_widget.setCurrentIndex(settings_index)
            QtWidgets.QApplication.processEvents()

            icon_slider: QtWidgets.QSlider = window.widgets[constants.WIDGET_ICON_SIZE_SLIDER]  # type: ignore[assignment]
            preview = window.widgets[constants.WIDGET_ICON_SIZE_LIVE_PREVIEW]
            preview_tiles = preview.findChildren(QtWidgets.QFrame, "icon_size_preview_tile")
            self.assertTrue(preview_tiles)
            old_width = preview_tiles[0].width()

            new_icon_size = min(icon_slider.maximum(), icon_slider.value() + 24)
            if new_icon_size == icon_slider.value():
                new_icon_size = max(icon_slider.minimum(), icon_slider.value() - 24)
            icon_slider.setValue(new_icon_size)
            QtWidgets.QApplication.processEvents()

            new_width = preview_tiles[0].width()
            self.assertNotEqual(old_width, new_width)
        finally:
            config_dir = window.config_dir
            window.close()
            shutil.rmtree(config_dir, ignore_errors=True)

    def test_icon_size_live_preview_reflects_grid_spacing_changes(self) -> None:
        window = self._create_window()
        try:
            settings_index = window.tab_widget.indexOf(window.settings_tab)
            self.assertGreaterEqual(settings_index, 0)
            window.tab_widget.setCurrentIndex(settings_index)
            QtWidgets.QApplication.processEvents()

            preview = window.widgets[constants.WIDGET_ICON_SIZE_LIVE_PREVIEW]
            grid_x_slider: QtWidgets.QSlider = window.widgets[constants.WIDGET_GRID_SPACING_X_SLIDER]  # type: ignore[assignment]
            grid_y_slider: QtWidgets.QSlider = window.widgets[constants.WIDGET_GRID_SPACING_Y_SLIDER]  # type: ignore[assignment]
            old_gap_x = int(preview.property("preview_grid_spacing_x") or 0)
            old_gap_y = int(preview.property("preview_grid_spacing_y") or 0)

            new_grid_x = min(grid_x_slider.maximum(), grid_x_slider.value() + 18)
            if new_grid_x == grid_x_slider.value():
                new_grid_x = max(grid_x_slider.minimum(), grid_x_slider.value() - 18)
            new_grid_y = min(grid_y_slider.maximum(), grid_y_slider.value() + 14)
            if new_grid_y == grid_y_slider.value():
                new_grid_y = max(grid_y_slider.minimum(), grid_y_slider.value() - 14)

            grid_x_slider.setValue(new_grid_x)
            grid_y_slider.setValue(new_grid_y)
            QtWidgets.QApplication.processEvents()

            new_gap_x = int(preview.property("preview_grid_spacing_x") or 0)
            new_gap_y = int(preview.property("preview_grid_spacing_y") or 0)
            self.assertNotEqual(old_gap_x, new_gap_x)
            self.assertNotEqual(old_gap_y, new_gap_y)
            self.assertEqual(new_grid_x, new_gap_x)
            self.assertEqual(new_grid_y, new_gap_y)
        finally:
            config_dir = window.config_dir
            window.close()
            shutil.rmtree(config_dir, ignore_errors=True)

    def test_icon_preview_background_updates_without_marking_settings_dirty(self) -> None:
        window = self._create_window()
        try:
            settings_index = window.tab_widget.indexOf(window.settings_tab)
            self.assertGreaterEqual(settings_index, 0)
            window.tab_widget.setCurrentIndex(settings_index)
            QtWidgets.QApplication.processEvents()

            preview = window.widgets[constants.WIDGET_ICON_SIZE_LIVE_PREVIEW]
            bg_input: QtWidgets.QLineEdit = window.widgets[constants.WIDGET_ICON_PREVIEW_BACKGROUND_COLOR_INPUT]  # type: ignore[assignment]
            self.assertFalse(window._settings_dirty)
            bg_input.setText("#334455")
            bg_input.editingFinished.emit()
            QtWidgets.QApplication.processEvents()

            self.assertEqual("#334455", str(preview.property("preview_background_color")))
            self.assertFalse(window._settings_dirty)
        finally:
            config_dir = window.config_dir
            window.close()
            shutil.rmtree(config_dir, ignore_errors=True)

    def test_settings_sliders_ignore_wheel_via_no_wheel_slider(self) -> None:
        window = self._create_window()
        try:
            for widget_name in (
                constants.WIDGET_ICON_SIZE_SLIDER,
                constants.WIDGET_TILE_FRAME_THICKNESS_SLIDER,
                constants.WIDGET_GRID_SPACING_X_SLIDER,
                constants.WIDGET_GRID_SPACING_Y_SLIDER,
                constants.WIDGET_SECTION_FONT_SIZE_SLIDER,
                constants.WIDGET_SECTION_LINE_THICKNESS_SLIDER,
            ):
                slider = window.widgets[widget_name]
                self.assertIsInstance(slider, NoWheelSlider)
        finally:
            config_dir = window.config_dir
            window.close()
            shutil.rmtree(config_dir, ignore_errors=True)

    def test_section_separator_live_preview_updates_when_controls_change(self) -> None:
        window = self._create_window()
        try:
            settings_index = window.tab_widget.indexOf(window.settings_tab)
            self.assertGreaterEqual(settings_index, 0)
            window.tab_widget.setCurrentIndex(settings_index)
            QtWidgets.QApplication.processEvents()

            preview = window.widgets[constants.WIDGET_SECTION_SEPARATOR_LIVE_PREVIEW]
            old_hint = preview.sizeHint().height()

            font_slider: QtWidgets.QSlider = window.widgets[constants.WIDGET_SECTION_FONT_SIZE_SLIDER]  # type: ignore[assignment]
            old_font = font_slider.value()
            new_font = min(font_slider.maximum(), old_font + 4)
            if new_font == old_font:
                new_font = max(font_slider.minimum(), old_font - 4)
            font_slider.setValue(new_font)

            gap_above_spinbox = window.widgets[constants.WIDGET_SECTION_GAP_ABOVE_SPINBOX]
            old_gap = int(gap_above_spinbox.value())
            gap_above_spinbox.setValue(min(gap_above_spinbox.maximum(), old_gap + 6))
            QtWidgets.QApplication.processEvents()

            new_hint = preview.sizeHint().height()
            self.assertNotEqual(old_hint, new_hint)
        finally:
            config_dir = window.config_dir
            window.close()
            shutil.rmtree(config_dir, ignore_errors=True)

    def test_toolbox_tab_background_color_applies_to_canvas_and_resets(self) -> None:
        window = self._create_window()
        try:
            ctx = window.toolbox_tabs[0]
            default_color = ctx.canvas.viewport().palette().color(QtGui.QPalette.ColorRole.Window).name()
            window._set_toolbox_tab_background_color(ctx, "#334455")
            QtWidgets.QApplication.processEvents()

            self.assertEqual("#334455", ctx.background_color)
            self.assertEqual(
                "#334455",
                ctx.canvas.viewport().palette().color(QtGui.QPalette.ColorRole.Window).name(),
            )
            self.assertEqual("", ctx.canvas.viewport().styleSheet())

            window._set_toolbox_tab_background_color(ctx, "")
            QtWidgets.QApplication.processEvents()

            self.assertEqual("", ctx.background_color)
            self.assertEqual("", ctx.canvas.viewport().styleSheet())
            self.assertEqual(
                default_color,
                ctx.canvas.viewport().palette().color(QtGui.QPalette.ColorRole.Window).name(),
            )
        finally:
            config_dir = window.config_dir
            window.close()
            shutil.rmtree(config_dir, ignore_errors=True)

    def test_image_file_preview_setting_applies_via_save_apply(self) -> None:
        window = self._create_window()
        try:
            settings_index = window.tab_widget.indexOf(window.settings_tab)
            self.assertGreaterEqual(settings_index, 0)
            window.tab_widget.setCurrentIndex(settings_index)
            QtWidgets.QApplication.processEvents()

            checkbox: QtWidgets.QCheckBox = window.widgets[constants.WIDGET_IMAGE_FILE_PREVIEW_CHECKBOX]  # type: ignore[assignment]
            original = window.current_image_file_preview_enabled()
            checkbox.setChecked(not original)
            QtWidgets.QApplication.processEvents()
            self.assertTrue(window._settings_dirty)

            window._apply_pending_settings()
            self.assertEqual(not original, window.current_image_file_preview_enabled())
        finally:
            config_dir = window.config_dir
            window.close()
            shutil.rmtree(config_dir, ignore_errors=True)

    def test_image_file_preview_mode_applies_via_save_apply(self) -> None:
        window = self._create_window()
        try:
            settings_index = window.tab_widget.indexOf(window.settings_tab)
            self.assertGreaterEqual(settings_index, 0)
            window.tab_widget.setCurrentIndex(settings_index)
            QtWidgets.QApplication.processEvents()

            combobox: QtWidgets.QComboBox = window.widgets[constants.WIDGET_IMAGE_FILE_PREVIEW_MODE_COMBOBOX]  # type: ignore[assignment]
            current_mode = window.current_image_file_preview_mode()
            target_mode = (
                constants.IMAGE_PREVIEW_MODE_FILL
                if current_mode == constants.IMAGE_PREVIEW_MODE_FIT
                else constants.IMAGE_PREVIEW_MODE_FIT
            )
            target_index = max(0, combobox.findData(target_mode))
            combobox.setCurrentIndex(target_index)
            QtWidgets.QApplication.processEvents()
            self.assertTrue(window._settings_dirty)

            window._apply_pending_settings()
            self.assertEqual(target_mode, window.current_image_file_preview_mode())
        finally:
            config_dir = window.config_dir
            window.close()
            shutil.rmtree(config_dir, ignore_errors=True)

    def test_video_file_preview_setting_applies_via_save_apply(self) -> None:
        window = self._create_window()
        try:
            settings_index = window.tab_widget.indexOf(window.settings_tab)
            self.assertGreaterEqual(settings_index, 0)
            window.tab_widget.setCurrentIndex(settings_index)
            QtWidgets.QApplication.processEvents()

            checkbox: QtWidgets.QCheckBox = window.widgets[constants.WIDGET_VIDEO_FILE_PREVIEW_CHECKBOX]  # type: ignore[assignment]
            original = window.current_video_file_preview_enabled()
            checkbox.setChecked(not original)
            QtWidgets.QApplication.processEvents()
            self.assertTrue(window._settings_dirty)

            window._apply_pending_settings()
            self.assertEqual(not original, window.current_video_file_preview_enabled())
        finally:
            config_dir = window.config_dir
            window.close()
            shutil.rmtree(config_dir, ignore_errors=True)

    def test_hover_preview_setting_applies_via_save_apply(self) -> None:
        window = self._create_window()
        try:
            settings_index = window.tab_widget.indexOf(window.settings_tab)
            self.assertGreaterEqual(settings_index, 0)
            window.tab_widget.setCurrentIndex(settings_index)
            QtWidgets.QApplication.processEvents()

            checkbox: QtWidgets.QCheckBox = window.widgets[constants.WIDGET_HOVER_PREVIEW_CHECKBOX]  # type: ignore[assignment]
            original = window.current_hover_preview_enabled()
            checkbox.setChecked(not original)
            QtWidgets.QApplication.processEvents()
            self.assertTrue(window._settings_dirty)

            window._apply_pending_settings()
            self.assertEqual(not original, window.current_hover_preview_enabled())
        finally:
            config_dir = window.config_dir
            window.close()
            shutil.rmtree(config_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
