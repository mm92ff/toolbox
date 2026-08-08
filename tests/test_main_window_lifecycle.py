from __future__ import annotations

import os
import uuid
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtGui, QtWidgets

from app.main_window import MainWindow


def _application() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _window(tmp_path) -> MainWindow:
    _application()
    app_name = f"ToolboxLifecycle-{uuid.uuid4().hex}"
    with patch.object(
        QtWidgets.QSystemTrayIcon,
        "isSystemTrayAvailable",
        return_value=False,
    ):
        return MainWindow(app_name, config_dir=tmp_path / app_name)


def test_close_without_available_tray_performs_shutdown(tmp_path) -> None:
    window = _window(tmp_path)
    window._minimize_to_tray = True
    event = QtGui.QCloseEvent()

    with patch.object(
        QtWidgets.QSystemTrayIcon,
        "isSystemTrayAvailable",
        return_value=False,
    ):
        window.closeEvent(event)

    assert event.isAccepted()
    assert window._closing is True
    assert window._shutdown_complete is True


def test_close_with_enabled_tray_hides_without_shutdown(tmp_path) -> None:
    window = _window(tmp_path)
    window.show()
    window._show_tray_icon = True
    window._minimize_to_tray = True
    tray = MagicMock()
    window.tray_icon = tray
    event = QtGui.QCloseEvent()

    with patch.object(
        QtWidgets.QSystemTrayIcon,
        "isSystemTrayAvailable",
        return_value=True,
    ):
        window.closeEvent(event)

    assert not event.isAccepted()
    assert not window.isVisible()
    assert window._shutdown_complete is False
    tray.showMessage.assert_called_once()

    window._force_quit = True
    window.close()


def test_tray_sync_controls_visibility_and_last_window_policy(tmp_path) -> None:
    app = _application()
    window = _window(tmp_path)
    tray = MagicMock()
    window.tray_icon = tray
    window._show_tray_icon = True
    window._minimize_to_tray = False

    with patch.object(
        QtWidgets.QSystemTrayIcon,
        "isSystemTrayAvailable",
        return_value=True,
    ):
        window._sync_tray_state()

    tray.setVisible.assert_called_once_with(True)
    assert app.quitOnLastWindowClosed() is True

    window._minimize_to_tray = True
    with patch.object(
        QtWidgets.QSystemTrayIcon,
        "isSystemTrayAvailable",
        return_value=True,
    ):
        window._sync_tray_state()
    assert tray.setVisible.call_args.args == (True,)
    assert app.quitOnLastWindowClosed() is False

    window._show_tray_icon = False
    with patch.object(
        QtWidgets.QSystemTrayIcon,
        "isSystemTrayAvailable",
        return_value=True,
    ):
        window._sync_tray_state()
    assert tray.setVisible.call_args.args == (False,)
    assert app.quitOnLastWindowClosed() is True
    window._force_quit = True
    window.close()


def test_close_does_not_minimize_when_tray_icon_is_disabled(tmp_path) -> None:
    window = _window(tmp_path)
    window._show_tray_icon = False
    window._minimize_to_tray = True
    window.tray_icon = MagicMock()
    event = QtGui.QCloseEvent()

    with patch.object(
        QtWidgets.QSystemTrayIcon,
        "isSystemTrayAvailable",
        return_value=True,
    ):
        window.closeEvent(event)

    assert event.isAccepted()
    assert window._shutdown_complete is True
    window.tray_icon.showMessage.assert_not_called()


def test_force_quit_bypasses_enabled_tray(tmp_path) -> None:
    window = _window(tmp_path)
    window._minimize_to_tray = True
    window._force_quit = True
    window.tray_icon = MagicMock()
    event = QtGui.QCloseEvent()

    with patch.object(
        QtWidgets.QSystemTrayIcon,
        "isSystemTrayAvailable",
        return_value=True,
    ):
        window.closeEvent(event)

    assert event.isAccepted()
    assert window._shutdown_complete is True
    window.tray_icon.showMessage.assert_not_called()


def test_shutdown_managers_and_persistence_run_only_once(tmp_path) -> None:
    window = _window(tmp_path)
    window.persist_toolbox_state = MagicMock()
    window._save_settings = MagicMock()
    window._size_service = MagicMock()
    window._folder_count_service = MagicMock()
    window._appimage_icon_service = MagicMock()
    window.desktop_process_manager = MagicMock()
    window._shutdown_broken_entries_scan_worker = MagicMock()

    window._begin_shutdown()
    window._begin_shutdown()

    window._size_service.shutdown.assert_called_once()
    window._folder_count_service.shutdown.assert_called_once()
    window._appimage_icon_service.shutdown.assert_called_once()
    window.desktop_process_manager.shutdown.assert_called_once()
    window.persist_toolbox_state.assert_called_once()
    window._save_settings.assert_called_once()
