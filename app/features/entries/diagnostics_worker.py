#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Background worker for broken-entry diagnostics scans."""

from __future__ import annotations

from PySide6 import QtCore

from app.domain.models import ToolboxTabData
from app.services.diagnostics import BrokenToolEntry, find_broken_tool_entries


class BrokenEntriesScanWorker(QtCore.QObject):
    """Scan toolbox snapshots for broken entries on a background thread."""

    finished = QtCore.Signal(object)
    failed = QtCore.Signal(str)

    def __init__(self, tab_snapshots: list[ToolboxTabData]) -> None:
        super().__init__()
        self._tab_snapshots = tab_snapshots

    @QtCore.Slot()
    def run(self) -> None:
        try:
            broken_entries = find_broken_tool_entries(self._tab_snapshots)
        except Exception as exc:  # pragma: no cover - defensive boundary
            self.failed.emit(str(exc))
            return
        self.finished.emit(broken_entries)


def clone_tab_snapshots(tabs: list[ToolboxTabData]) -> list[ToolboxTabData]:
    """Create detached tab snapshots for thread-safe diagnostics scanning."""
    return [
        ToolboxTabData(
            title=tab.title,
            entries=list(tab.entries),
            tab_id=tab.tab_id,
            is_primary=tab.is_primary,
        )
        for tab in tabs
    ]


def coerce_broken_entries(payload: object) -> list[BrokenToolEntry]:
    """Return validated broken-entry results from a generic signal payload."""
    if not isinstance(payload, list):
        return []
    if not all(isinstance(item, BrokenToolEntry) for item in payload):
        return []
    return payload
