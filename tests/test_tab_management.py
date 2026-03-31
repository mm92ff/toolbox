import os
import shutil
import unittest
import uuid
import weakref

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets

from app import constants
from app.main_window import MainWindow


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


if __name__ == "__main__":
    unittest.main()
