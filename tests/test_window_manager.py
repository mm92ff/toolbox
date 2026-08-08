from __future__ import annotations

import os
import uuid
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtGui, QtWidgets

from app.window_manager import WindowManager


def _application() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_create_activate_preferred_tab_and_close_one_window(tmp_path) -> None:
    app = _application()
    with patch.object(QtWidgets.QSystemTrayIcon, "isSystemTrayAvailable", return_value=False):
        manager = WindowManager(
            f"Manager-{uuid.uuid4().hex}", tmp_path, parent=app
        )
        first = manager.create_window()
        second_tab_id = manager.repository.create_tab("Second")
        second = manager.create_window(second_tab_id)
        assert len(manager.windows) == 2
        assert second.current_toolbox_context().tab_id == second_tab_id

        event = QtGui.QCloseEvent()
        first.closeEvent(event)
        assert event.isAccepted()
        assert manager.windows == (second,)
        assert second._closing is False
        manager.shutdown()


def test_ctrl_n_signal_creates_exactly_one_window(tmp_path) -> None:
    app = _application()
    with patch.object(QtWidgets.QSystemTrayIcon, "isSystemTrayAvailable", return_value=False):
        manager = WindowManager(
            f"Shortcut-{uuid.uuid4().hex}", tmp_path, parent=app
        )
        first = manager.create_window()
        first.new_window_requested.emit()
        assert len(manager.windows) == 2
        manager.shutdown()


def test_shared_services_live_until_manager_shutdown(tmp_path) -> None:
    app = _application()
    with patch.object(QtWidgets.QSystemTrayIcon, "isSystemTrayAvailable", return_value=False):
        manager = WindowManager(
            f"Lifecycle-{uuid.uuid4().hex}", tmp_path, parent=app
        )
        first = manager.create_window()
        manager.create_window()
        folder_shutdown = MagicMock()
        icon_shutdown = MagicMock()
        manager.folder_count_service.shutdown = folder_shutdown
        manager.appimage_icon_service.shutdown = icon_shutdown

        first.close()
        folder_shutdown.assert_not_called()
        icon_shutdown.assert_not_called()
        manager.shutdown()
        manager.shutdown()
        folder_shutdown.assert_called_once()
        icon_shutdown.assert_called_once()


def test_last_window_hides_when_managed_tray_mode_is_enabled(tmp_path) -> None:
    app = _application()
    with patch.object(QtWidgets.QSystemTrayIcon, "isSystemTrayAvailable", return_value=True):
        manager = WindowManager(
            f"Tray-{uuid.uuid4().hex}", tmp_path, parent=app
        )
        window = manager.create_window()
        window.show()
        manager._show_tray_icon = True
        manager._minimize_to_tray = True
        manager.tray.notify_hidden = MagicMock()
        event = QtGui.QCloseEvent()

        window.closeEvent(event)

        assert not event.isAccepted()
        assert window in manager.windows
        assert not window.isVisible()
        manager.tray.notify_hidden.assert_called_once()
        manager.shutdown()
