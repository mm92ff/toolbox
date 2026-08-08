from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6 import QtWidgets

from app.domain.models import ToolboxEntry
from app.state.toolbox_repository import StaleToolboxStateError, ToolboxStateRepository


def _application() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_repository_snapshots_are_defensive_and_commands_are_global(tmp_path) -> None:
    _application()
    repository = ToolboxStateRepository(tmp_path, debounce_ms=0)
    first = repository.snapshot()[0]
    first.title = "Externally changed"
    assert repository.snapshot()[0].title != "Externally changed"

    tab_id = repository.create_tab("Work", origin_window_id="a")
    entry = ToolboxEntry(title="Tool", path="/tmp/tool")
    assert repository.add_entries(tab_id, [entry], origin_window_id="a")
    assert repository.move_entries(tab_id, {entry.entry_id: (40, 50)})
    assert repository.revision == 3
    assert repository.tab(tab_id).entries[0].x == 40

    assert repository.undo("b")
    assert repository.tab(tab_id).entries[0].x != 40
    assert repository.redo("a")
    assert repository.tab(tab_id).entries[0].x == 40


def test_repository_noops_and_invariants(tmp_path) -> None:
    _application()
    repository = ToolboxStateRepository(tmp_path, debounce_ms=0)
    tab = repository.snapshot()[0]
    assert repository.rename_tab(tab.tab_id, tab.title) is False
    assert repository.revision == 0
    with pytest.raises(ValueError):
        repository.delete_tab(tab.tab_id)
    with pytest.raises(KeyError):
        repository.rename_tab("missing", "Nope")


def test_repository_debounces_writes_and_flushes(tmp_path, monkeypatch) -> None:
    _application()
    writes: list[list[object]] = []

    def record_write(_config_dir, tabs) -> None:
        writes.append(list(tabs))

    monkeypatch.setattr(
        "app.state.toolbox_repository.save_toolbox_tabs", record_write
    )
    repository = ToolboxStateRepository(tmp_path, debounce_ms=10_000)
    repository.create_tab("A")
    repository.create_tab("B")
    assert writes == []
    assert repository.flush() is True
    assert len(writes) == 1


def test_persistence_failure_is_reported_without_losing_memory_state(
    tmp_path, monkeypatch
) -> None:
    _application()
    repository = ToolboxStateRepository(tmp_path, debounce_ms=10_000)
    failures: list[str] = []
    repository.persistence_failed.connect(failures.append)
    repository.create_tab("Still in memory")

    def fail_write(_config_dir, _tabs) -> None:
        raise OSError("disk unavailable")

    monkeypatch.setattr("app.state.toolbox_repository.save_toolbox_tabs", fail_write)
    assert repository.flush() is False
    assert failures == ["disk unavailable"]
    assert [tab.title for tab in repository.snapshot()][-1] == "Still in memory"


def test_expected_revision_rejects_stale_complete_snapshot(tmp_path) -> None:
    _application()
    repository = ToolboxStateRepository(tmp_path, debounce_ms=0)
    stale = repository.snapshot_dicts()
    repository.create_tab("Newer")

    with pytest.raises(StaleToolboxStateError):
        repository.replace(stale, expected_revision=0)

    assert [tab.title for tab in repository.snapshot()][-1] == "Newer"
