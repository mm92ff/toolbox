from __future__ import annotations

import os
import json
import uuid
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtTest, QtWidgets

from app import constants
from app.domain.models import ToolboxEntry
from app.window_manager import WindowManager


def _application() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _process_events_for(milliseconds: int) -> None:
    loop = QtCore.QEventLoop()
    QtCore.QTimer.singleShot(milliseconds, loop.quit)
    loop.exec()


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


def test_responsive_setting_syncs_but_column_counts_stay_window_local(tmp_path) -> None:
    app = _application()
    with patch.object(QtWidgets.QSystemTrayIcon, "isSystemTrayAvailable", return_value=False):
        manager = WindowManager(
            f"ResponsiveSync-{uuid.uuid4().hex}", tmp_path, parent=app
        )
        first = manager.create_window()
        second = manager.create_window()
        first_ctx = first.current_toolbox_context()
        second_ctx = second.current_toolbox_context()
        assert first_ctx is not None
        assert second_ctx is not None
        first_ctx.entries.extend(
            ToolboxEntry(title=f"Tool {index}", path=f"/tmp/tool-{index}")
            for index in range(8)
        )
        first.persist_toolbox_state()

        first.widgets[
            constants.WIDGET_RESPONSIVE_TOOLBOX_LAYOUT_CHECKBOX
        ].setChecked(True)
        first._apply_pending_settings()

        assert first.current_responsive_toolbox_layout() is True
        assert second.current_responsive_toolbox_layout() is True
        assert first_ctx.canvas.responsive_layout_enabled() is True
        assert second_ctx.canvas.responsive_layout_enabled() is True
        first_ctx.canvas.surface.set_viewport_width(900)
        second_ctx.canvas.surface.set_viewport_width(260)
        assert first_ctx.canvas.responsive_columns() > second_ctx.canvas.responsive_columns()
        manager.shutdown()


def test_responsive_resize_does_not_commit_persist_or_add_undo(tmp_path) -> None:
    app = _application()
    config_dir = tmp_path / "config"
    with patch.object(QtWidgets.QSystemTrayIcon, "isSystemTrayAvailable", return_value=False):
        manager = WindowManager(
            f"ResponsiveNoCommit-{uuid.uuid4().hex}", config_dir, parent=app
        )
        window = manager.create_window()
        ctx = window.current_toolbox_context()
        assert ctx is not None
        ctx.entries.extend(
            ToolboxEntry(title=f"Tool {index}", path=f"/tmp/tool-{index}")
            for index in range(8)
        )
        window.persist_toolbox_state()
        manager.repository.flush()
        window.widgets[
            constants.WIDGET_RESPONSIVE_TOOLBOX_LAYOUT_CHECKBOX
        ].setChecked(True)
        window._apply_pending_settings()
        tools_path = config_dir / constants.TOOL_CONFIG_FILENAME
        tools_before = tools_path.read_bytes()
        revision_before = manager.repository.revision
        undo_steps_before = len(manager.repository._undo_stack)
        state_changes = QtTest.QSignalSpy(manager.repository.state_changed)

        for width in (900, 700, 500, 300, 700):
            ctx.canvas.surface.set_viewport_width(width)
        manager.repository.flush()

        assert manager.repository.revision == revision_before
        assert len(manager.repository._undo_stack) == undo_steps_before
        assert state_changes.count() == 0
        assert tools_path.read_bytes() == tools_before
        manager.shutdown()


def test_responsive_drag_attempt_is_blocked_with_status_hint(tmp_path) -> None:
    app = _application()
    with patch.object(QtWidgets.QSystemTrayIcon, "isSystemTrayAvailable", return_value=False):
        manager = WindowManager(
            f"ResponsiveDrag-{uuid.uuid4().hex}", tmp_path, parent=app
        )
        window = manager.create_window()
        ctx = window.current_toolbox_context()
        assert ctx is not None
        entry = ToolboxEntry(title="Tool", path="/tmp/tool")
        ctx.entries.append(entry)
        window.persist_toolbox_state()
        window.widgets[
            constants.WIDGET_RESPONSIVE_TOOLBOX_LAYOUT_CHECKBOX
        ].setChecked(True)
        window._apply_pending_settings()
        window.refresh_canvas(ctx)
        window.show()
        app.processEvents()
        widget = ctx.canvas.surface._widgets[entry.entry_id]
        canonical_position = (entry.x, entry.y)

        QtTest.QTest.mousePress(
            widget,
            QtCore.Qt.MouseButton.LeftButton,
            pos=widget.rect().center(),
        )
        QtTest.QTest.qWait(constants.MOVE_HOLD_DELAY_MS + 40)
        QtTest.QTest.mouseRelease(
            widget,
            QtCore.Qt.MouseButton.LeftButton,
            pos=widget.rect().center(),
        )

        assert "Manuelles Verschieben" in window.status.currentMessage()
        assert (entry.x, entry.y) == canonical_position
        assert widget.acceptDrops() is True
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


def test_folder_icon_size_sync_is_path_local_and_persisted(tmp_path) -> None:
    app = _application()
    shared_folder = tmp_path / "shared"
    other_folder = tmp_path / "other"
    shared_folder.mkdir()
    other_folder.mkdir()
    (shared_folder / "file.txt").write_text("data", encoding="utf-8")
    with patch.object(QtWidgets.QSystemTrayIcon, "isSystemTrayAvailable", return_value=False):
        manager = WindowManager(
            f"FolderAppearance-{uuid.uuid4().hex}", tmp_path / "config", parent=app
        )
        first = manager.create_window()
        second = manager.create_window()
        first_ctx = first.current_toolbox_context()
        second_ctx = second.current_toolbox_context()
        assert first_ctx is not None
        assert second_ctx is not None
        first._enter_folder_browse(first_ctx, shared_folder)
        second._enter_folder_browse(second_ctx, shared_folder)
        manager.repository.flush()
        tools_path = tmp_path / "config" / constants.TOOL_CONFIG_FILENAME
        tools_before = tools_path.read_bytes()
        initial_repository_revision = manager.repository.revision
        first_ctx.selected_ids = {first_ctx._browse_display_entries[0].entry_id}
        first_ctx.canvas.select_entries(first_ctx.selected_ids)
        second.widgets[constants.WIDGET_GRID_SPACING_X_SLIDER].setValue(77)
        assert second._settings_dirty is True

        with patch("app.features.entries.folder_browse._make_browse_entries") as relist:
            first_ctx.browse_icon_size_slider.setValue(120)
            first._commit_folder_icon_size_change(first_ctx)
            relist.assert_not_called()

        assert second_ctx.browse_icon_size_slider.value() == 120
        assert second._shared_settings_conflict is False
        assert first_ctx.selected_ids == {first_ctx._browse_display_entries[0].entry_id}
        assert manager.repository.revision == initial_repository_revision
        assert tools_path.read_bytes() == tools_before
        payload = json.loads((tmp_path / "config" / constants.UI_SETTINGS_FILENAME).read_text())
        overrides = payload["ui_settings"]["folder_browse"]["icon_size_overrides"]
        assert overrides[str(shared_folder.resolve())]["size"] == 120

        second._exit_folder_browse(second_ctx)
        second._enter_folder_browse(second_ctx, other_folder)
        assert second_ctx.browse_icon_size_slider.value() == second.current_icon_size()

        first_ctx.browse_icon_size_slider.setValue(132)
        first._commit_folder_icon_size_change(first_ctx)
        assert second_ctx.browse_icon_size_slider.value() == second.current_icon_size()

        first._reset_folder_icon_size(first_ctx)
        assert first_ctx.browse_icon_size_slider.value() == first.current_icon_size()
        payload = json.loads((tmp_path / "config" / constants.UI_SETTINGS_FILENAME).read_text())
        overrides = payload["ui_settings"]["folder_browse"]["icon_size_overrides"]
        assert str(shared_folder.resolve()) not in overrides
        manager.shutdown()


def test_folder_icon_size_is_restored_after_restart(tmp_path) -> None:
    app = _application()
    config_dir = tmp_path / "config"
    folder = tmp_path / "remembered"
    folder.mkdir()
    app_name = f"FolderRestart-{uuid.uuid4().hex}"
    with patch.object(QtWidgets.QSystemTrayIcon, "isSystemTrayAvailable", return_value=False):
        first_manager = WindowManager(app_name, config_dir, parent=app)
        first_window = first_manager.create_window()
        first_ctx = first_window.current_toolbox_context()
        assert first_ctx is not None
        first_window._enter_folder_browse(first_ctx, folder)
        first_ctx.browse_icon_size_slider.setValue(112)
        first_window._commit_folder_icon_size_change(first_ctx)
        first_manager.shutdown()

        second_manager = WindowManager(app_name, config_dir, parent=app)
        second_window = second_manager.create_window()
        second_ctx = second_window.current_toolbox_context()
        assert second_ctx is not None
        second_window._enter_folder_browse(second_ctx, folder)

        assert second_ctx.browse_icon_size_slider.value() == 112
        second_manager.shutdown()


def test_folder_icon_slider_throttles_100_events_with_500_entries(tmp_path) -> None:
    app = _application()
    folder = tmp_path / "large-folder"
    folder.mkdir()
    for index in range(500):
        (folder / f"file-{index:03d}.txt").touch()
    with patch.object(QtWidgets.QSystemTrayIcon, "isSystemTrayAvailable", return_value=False):
        manager = WindowManager(
            f"FolderThrottle-{uuid.uuid4().hex}", tmp_path / "config", parent=app
        )
        window = manager.create_window()
        ctx = window.current_toolbox_context()
        assert ctx is not None
        window._enter_folder_browse(ctx, folder)
        assert len(ctx._browse_display_entries) == 500

        original_layout = ctx.canvas.apply_layout_settings
        original_persist = window._persist_folder_browse_settings
        with (
            patch.object(
                ctx.canvas,
                "apply_layout_settings",
                wraps=original_layout,
            ) as layout_update,
            patch.object(
                window,
                "_persist_folder_browse_settings",
                wraps=original_persist,
            ) as persist,
            patch("app.features.entries.folder_browse._make_browse_entries") as relist,
        ):
            for index in range(100):
                ctx.browse_icon_size_slider.setValue(40 + (index % 31) * 4)
            _process_events_for(constants.BROWSE_ICON_SIZE_LAYOUT_INTERVAL_MS + 30)

            assert 1 <= layout_update.call_count <= 2
            assert persist.call_count == 0
            relist.assert_not_called()

            for value in (92, 100, 108, 116, 124):
                ctx.browse_icon_size_slider.setValue(value)
            _process_events_for(constants.BROWSE_ICON_SIZE_LAYOUT_INTERVAL_MS + 30)
            window._commit_folder_icon_size_change(ctx)

            assert layout_update.call_count <= 4
            assert persist.call_count == 1
            relist.assert_not_called()
        manager.shutdown()


def test_folder_icon_size_write_failure_keeps_in_memory_value(tmp_path) -> None:
    app = _application()
    folder = tmp_path / "folder"
    folder.mkdir()
    with patch.object(QtWidgets.QSystemTrayIcon, "isSystemTrayAvailable", return_value=False):
        manager = WindowManager(
            f"FolderWriteError-{uuid.uuid4().hex}", tmp_path / "config", parent=app
        )
        window = manager.create_window()
        manager.folder_browse_appearance.set_icon_size(folder, 128)

        with patch.object(window, "_write_json_atomic", side_effect=OSError("disk full")):
            assert window._persist_folder_browse_settings() is False

        assert manager.folder_browse_appearance.get_override(folder) == 128
        assert "disk full" in window.status.currentMessage()
        manager.shutdown()
