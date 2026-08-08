from __future__ import annotations

import os
import uuid
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets

from app.domain.models import ToolboxEntry
from app.window_manager import WindowManager


def _application() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _manager(tmp_path) -> WindowManager:
    app = _application()
    return WindowManager(
        f"MultiWindow-{uuid.uuid4().hex}", tmp_path, parent=app
    )


def test_two_windows_share_mutations_and_global_undo(tmp_path) -> None:
    with patch.object(QtWidgets.QSystemTrayIcon, "isSystemTrayAvailable", return_value=False):
        manager = _manager(tmp_path)
        first = manager.create_window()
        second = manager.create_window()
        first_ctx = first.current_toolbox_context()
        second_ctx = second.current_toolbox_context()
        first_ctx.search_input.setText("first-only")
        second_ctx.search_input.setText("second-only")

        first_ctx.entries.append(ToolboxEntry(title="Tool", path="/tmp/tool"))
        first.persist_toolbox_state()

        assert [entry.title for entry in second.toolbox_tabs[0].entries] == ["Tool"]
        assert first_ctx.search_input.text() == "first-only"
        assert second.toolbox_tabs[0].search_input.text() == "second-only"

        second._undo_last_toolbox_change()
        assert first.toolbox_tabs[0].entries == []
        assert second.toolbox_tabs[0].entries == []
        manager.shutdown()


def test_tab_creation_is_broadcast_without_recursive_commit(tmp_path) -> None:
    with patch.object(QtWidgets.QSystemTrayIcon, "isSystemTrayAvailable", return_value=False):
        manager = _manager(tmp_path)
        first = manager.create_window()
        second = manager.create_window()
        first._create_new_toolbox_tab()
        assert len(first.toolbox_tabs) == 2
        assert len(second.toolbox_tabs) == 2
        assert manager.repository.revision == 1
        manager.shutdown()


def test_active_tabs_remain_window_local_during_entry_sync(tmp_path) -> None:
    with patch.object(QtWidgets.QSystemTrayIcon, "isSystemTrayAvailable", return_value=False):
        manager = _manager(tmp_path)
        first = manager.create_window()
        second_tab_id = manager.repository.create_tab("Second")
        second = manager.create_window(second_tab_id)
        first_tab_id = first.toolbox_tabs[0].tab_id
        first.tab_widget.setCurrentWidget(first.toolbox_tabs[0].page)

        first.toolbox_tabs[0].entries.append(
            ToolboxEntry(title="Synced", path="/tmp/synced")
        )
        first.persist_toolbox_state()

        assert first.current_toolbox_context().tab_id == first_tab_id
        assert second.current_toolbox_context().tab_id == second_tab_id
        manager.shutdown()


def test_structural_broadcast_preserves_existing_view_and_model_identity(tmp_path) -> None:
    with patch.object(QtWidgets.QSystemTrayIcon, "isSystemTrayAvailable", return_value=False):
        manager = _manager(tmp_path)
        first = manager.create_window()
        second = manager.create_window()
        second_ctx = second.toolbox_tabs[0]
        second_ctx.search_input.setText("local search")
        entry = ToolboxEntry(title="Retained", path="/tmp/retained")
        first.toolbox_tabs[0].entries.append(entry)
        first.persist_toolbox_state()
        second_entry = second_ctx.entries[0]

        manager.repository.create_tab("Structural change", origin_window_id=first.window_id)

        assert second.toolbox_tabs[0] is second_ctx
        assert second.toolbox_tabs[0].entries[0] is second_entry
        assert second_ctx.search_input.text() == "local search"
        manager.shutdown()


def test_external_rename_updates_active_window_title(tmp_path) -> None:
    with patch.object(QtWidgets.QSystemTrayIcon, "isSystemTrayAvailable", return_value=False):
        manager = _manager(tmp_path)
        first = manager.create_window()
        second = manager.create_window()
        tab_id = first.toolbox_tabs[0].tab_id

        manager.repository.rename_tab(tab_id, "Renamed", origin_window_id=first.window_id)

        assert second.windowTitle().endswith("— Renamed")
        manager.shutdown()


def test_stale_view_snapshot_cannot_overwrite_newer_repository_state(tmp_path) -> None:
    with patch.object(QtWidgets.QSystemTrayIcon, "isSystemTrayAvailable", return_value=False):
        manager = _manager(tmp_path)
        first = manager.create_window()
        manager.repository.create_tab("Newer")
        first._shared_state_revision = 0
        first.toolbox_tabs[0].entries.append(
            ToolboxEntry(title="Stale", path="/tmp/stale")
        )

        first.persist_toolbox_state()

        assert all(
            entry.title != "Stale"
            for tab in manager.repository.snapshot()
            for entry in tab.entries
        )
        assert len(first.toolbox_tabs) == 2
        manager.shutdown()
