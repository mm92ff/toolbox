#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnostics behavior for toolbox entries."""

from __future__ import annotations

from collections.abc import Callable

from PySide6 import QtCore, QtWidgets

from app import constants
from app.domain.models import ToolboxTabData
from app.features.entries.diagnostics_worker import (
    BrokenEntriesScanWorker,
    clone_tab_snapshots,
    coerce_broken_entries,
)
from app.services.diagnostics import BrokenToolEntry, find_broken_tool_entries


class BrokenEntriesScanUiRelay(QtCore.QObject):
    """Deliver worker results to UI handlers on the main thread."""

    def __init__(self, owner: "MainWindowEntryDiagnosticsMixin") -> None:
        super().__init__(owner)  # type: ignore[arg-type]
        self._owner = owner

    @QtCore.Slot(object)
    def on_scan_finished(self, payload: object) -> None:
        self._owner._on_broken_entries_scan_finished(payload)

    @QtCore.Slot(str)
    def on_scan_failed(self, error_message: str) -> None:
        self._owner._on_broken_entries_scan_failed(error_message)


class MainWindowEntryDiagnosticsMixin:
    def _close_active_broken_entries_dialog(self) -> None:
        active_dialog = getattr(self, "_active_broken_entries_dialog", None)
        if isinstance(active_dialog, QtWidgets.QMessageBox):
            active_dialog.close()
            active_dialog.deleteLater()
        self._active_broken_entries_dialog = None

    def _show_non_blocking_message(
        self,
        title: str,
        text: str,
        icon: QtWidgets.QMessageBox.Icon,
        buttons: QtWidgets.QMessageBox.StandardButton,
        default_button: QtWidgets.QMessageBox.StandardButton,
        on_finished: Callable[[QtWidgets.QMessageBox.StandardButton], None] | None = None,
    ) -> None:
        self._close_active_broken_entries_dialog()
        box = QtWidgets.QMessageBox(self)
        box.setWindowTitle(title)
        box.setText(text)
        box.setIcon(icon)
        box.setStandardButtons(buttons)
        box.setDefaultButton(default_button)
        box.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        # Native message boxes can become unresponsive on some Windows setups
        # while the parent window is busy with repaint/layout work.
        box.setOption(QtWidgets.QMessageBox.Option.DontUseNativeDialog, True)
        box.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
        if callable(on_finished):
            box.finished.connect(
                lambda result: on_finished(QtWidgets.QMessageBox.StandardButton(result))
            )
        box.destroyed.connect(lambda *_: setattr(self, "_active_broken_entries_dialog", None))
        self._active_broken_entries_dialog = box
        box.open()

    def _broken_entries_scan_ui_relay(self) -> BrokenEntriesScanUiRelay:
        relay = getattr(self, "_broken_entries_scan_ui_relay_obj", None)
        if relay is None:
            relay = BrokenEntriesScanUiRelay(self)
            self._broken_entries_scan_ui_relay_obj = relay
        return relay

    def _set_broken_entries_check_busy(self, busy: bool) -> None:
        check_button = self.widgets.get(constants.BUTTON_CHECK_BROKEN_ENTRIES)
        if check_button is not None:
            check_button.setEnabled(not busy)
            check_button.setText("Checking..." if busy else "Check Broken Entries")

    def _cleanup_broken_entries_scan_worker(self) -> None:
        self._broken_entries_scan_worker = None
        self._broken_entries_scan_thread = None
        self._set_broken_entries_check_busy(False)

    def _shutdown_broken_entries_scan_worker(self) -> None:
        thread = getattr(self, "_broken_entries_scan_thread", None)
        if thread is None:
            return
        thread.quit()
        thread.wait(2500)
        self._cleanup_broken_entries_scan_worker()

    def _collect_broken_tool_entries(self) -> list[BrokenToolEntry]:
        tab_snapshots = [
            ToolboxTabData(
                title=ctx.title,
                entries=list(ctx.entries),
                tab_id=ctx.tab_id,
                is_primary=ctx.is_primary,
            )
            for ctx in self.toolbox_tabs
        ]
        return find_broken_tool_entries(tab_snapshots)

    def _collect_broken_tool_snapshots(self) -> list[ToolboxTabData]:
        tabs = [
            ToolboxTabData(
                title=ctx.title,
                entries=list(ctx.entries),
                tab_id=ctx.tab_id,
                is_primary=ctx.is_primary,
            )
            for ctx in self.toolbox_tabs
        ]
        return clone_tab_snapshots(tabs)

    def _remove_broken_tool_entries(self, broken_entries: list[BrokenToolEntry]) -> int:
        broken_by_tab: dict[str, set[str]] = {}
        for item in broken_entries:
            broken_by_tab.setdefault(item.tab_id, set()).add(item.entry_id)

        removed_total = 0
        for ctx in self.toolbox_tabs:
            broken_ids = broken_by_tab.get(ctx.tab_id)
            if not broken_ids:
                continue

            removed_tools = any(
                entry.is_tool and entry.entry_id in broken_ids for entry in ctx.entries
            )
            before_count = len(ctx.entries)
            ctx.entries = [entry for entry in ctx.entries if entry.entry_id not in broken_ids]
            ctx.selected_ids.difference_update(broken_ids)
            removed_total += before_count - len(ctx.entries)

            if removed_tools and self.current_auto_compact_left():
                ctx.canvas.compact_tools(ctx.entries)

        if removed_total > 0:
            self.persist_toolbox_state()
            self.refresh_all_canvases()
        return removed_total

    def _show_broken_entries_dialog(self, broken_entries: list[BrokenToolEntry]) -> None:
        if not broken_entries:
            self._show_non_blocking_message(
                "Check Broken Entries",
                "No broken entries found.",
                QtWidgets.QMessageBox.Icon.Information,
                QtWidgets.QMessageBox.StandardButton.Ok,
                QtWidgets.QMessageBox.StandardButton.Ok,
            )
            self.status.showMessage("Check complete: no broken entries found.", 3000)
            return

        preview_limit = 18
        preview_lines: list[str] = []
        for item in broken_entries[:preview_limit]:
            preview_lines.append(f"- [{item.tab_title}] {item.entry_title}")
            preview_lines.append(f"  {item.path} ({item.reason})")
        remaining = len(broken_entries) - preview_limit
        if remaining > 0:
            preview_lines.append(f"... and {remaining} more")

        message = (
            f"{len(broken_entries)} broken entries found.\n\n"
            + "\n".join(preview_lines)
            + "\n\nRemove these entries now?"
        )
        self._show_non_blocking_message(
            "Broken Entries Found",
            message,
            QtWidgets.QMessageBox.Icon.Warning,
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
            lambda answer: self._on_broken_entries_choice_made(broken_entries, answer),
        )

    def _on_broken_entries_choice_made(
        self,
        broken_entries: list[BrokenToolEntry],
        answer: QtWidgets.QMessageBox.StandardButton,
    ) -> None:
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            self.status.showMessage("Check complete: broken entries were not removed.", 3000)
            return

        removed_total = self._remove_broken_tool_entries(broken_entries)
        if removed_total <= 0:
            self.status.showMessage("No entries removed.", 3000)
            return

        self._show_non_blocking_message(
            "Cleanup Complete",
            f"{removed_total} broken entries were removed.",
            QtWidgets.QMessageBox.Icon.Information,
            QtWidgets.QMessageBox.StandardButton.Ok,
            QtWidgets.QMessageBox.StandardButton.Ok,
        )
        self.status.showMessage(f"{removed_total} broken entries removed.", 3500)

    @QtCore.Slot(object)
    def _on_broken_entries_scan_finished(self, payload: object) -> None:
        self._show_broken_entries_dialog(coerce_broken_entries(payload))

    @QtCore.Slot(str)
    def _on_broken_entries_scan_failed(self, error_message: str) -> None:
        message = (error_message or "Unexpected diagnostics error.").strip()
        self._show_non_blocking_message(
            "Check Broken Entries",
            message,
            QtWidgets.QMessageBox.Icon.Critical,
            QtWidgets.QMessageBox.StandardButton.Ok,
            QtWidgets.QMessageBox.StandardButton.Ok,
        )
        self.status.showMessage("Broken-entries check failed.", 3000)

    def _run_broken_entries_check(self) -> None:
        if getattr(self, "_broken_entries_scan_thread", None) is not None:
            return
        snapshots = self._collect_broken_tool_snapshots()
        self._set_broken_entries_check_busy(True)
        self.status.showMessage("Checking for broken entries...", 3000)
        relay = self._broken_entries_scan_ui_relay()

        thread = QtCore.QThread(self)
        worker = BrokenEntriesScanWorker(snapshots)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(relay.on_scan_finished, QtCore.Qt.ConnectionType.QueuedConnection)
        worker.failed.connect(relay.on_scan_failed, QtCore.Qt.ConnectionType.QueuedConnection)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(
            self._cleanup_broken_entries_scan_worker,
            QtCore.Qt.ConnectionType.QueuedConnection,
        )

        self._broken_entries_scan_worker = worker
        self._broken_entries_scan_thread = thread
        thread.start()
