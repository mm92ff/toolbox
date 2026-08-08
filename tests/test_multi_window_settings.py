from __future__ import annotations

import os
import uuid
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets

from app import constants
from app.window_manager import WindowManager


def _application() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_applied_settings_broadcast_and_stale_draft_detection(tmp_path) -> None:
    app = _application()
    with patch.object(QtWidgets.QSystemTrayIcon, "isSystemTrayAvailable", return_value=False):
        manager = WindowManager(
            f"Settings-{uuid.uuid4().hex}", tmp_path, parent=app
        )
        first = manager.create_window()
        second = manager.create_window()

        second.widgets[constants.WIDGET_GRID_SPACING_X_SLIDER].setValue(77)
        assert second._settings_dirty
        first.widgets[constants.WIDGET_ICON_SIZE_SLIDER].setValue(96)
        first._apply_pending_settings()

        assert manager.settings.revision == 1
        assert second._shared_settings_conflict is True

        second._clear_settings_dirty()
        second._reload_shared_settings()
        assert second.current_icon_size() == 96
        manager.shutdown()


def test_clean_settings_view_updates_immediately(tmp_path) -> None:
    app = _application()
    with patch.object(QtWidgets.QSystemTrayIcon, "isSystemTrayAvailable", return_value=False):
        manager = WindowManager(
            f"SettingsSync-{uuid.uuid4().hex}", tmp_path, parent=app
        )
        first = manager.create_window()
        second = manager.create_window()
        first.widgets[constants.WIDGET_ICON_SIZE_SLIDER].setValue(104)
        first._apply_pending_settings()

        assert second._shared_settings_conflict is False
        assert second.current_icon_size() == 104
        manager.shutdown()


def test_stale_settings_draft_can_be_explicitly_applied(tmp_path) -> None:
    app = _application()
    with patch.object(QtWidgets.QSystemTrayIcon, "isSystemTrayAvailable", return_value=False):
        manager = WindowManager(
            f"SettingsOverwrite-{uuid.uuid4().hex}", tmp_path, parent=app
        )
        first = manager.create_window()
        second = manager.create_window()
        second.widgets[constants.WIDGET_ICON_SIZE_SLIDER].setValue(120)
        first.widgets[constants.WIDGET_ICON_SIZE_SLIDER].setValue(88)
        first._apply_pending_settings()
        assert second._shared_settings_conflict

        with patch.object(
            QtWidgets.QMessageBox,
            "question",
            return_value=QtWidgets.QMessageBox.StandardButton.No,
        ):
            second._apply_pending_settings()

        assert first.current_icon_size() == 120
        assert manager.settings.revision == 2
        manager.shutdown()
