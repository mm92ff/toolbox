#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Launching and launch-option behavior for toolbox entries."""

from __future__ import annotations

import logging
from pathlib import Path
import sys
from typing import Optional

from PySide6 import QtCore, QtWidgets

from app.domain.models import ToolboxEntry
from app.domain.tab_context import ToolboxTabContext
from app.services.desktop_entries import (
    DesktopLaunchInput,
    DesktopLaunchItem,
)
from app.services.desktop_entry_launch import prepare_desktop_launch
from app.services.system_utils import launch_path, open_directory_in_os
from app.ui.widgets.input_controls import NoWheelComboBox

logger = logging.getLogger(__name__)


class MainWindowEntryLaunchingMixin:
    @staticmethod
    def _entry_target_log_label(entry: ToolboxEntry) -> str:
        path = Path(entry.path).expanduser()
        target_name = path.name.strip() or path.stem.strip() or "<unknown>"
        return f"{entry.title} [{target_name}]"

    def _prompt_launch_options(
        self,
        entry: ToolboxEntry,
        *,
        title: str,
        initial_arguments: str,
        initial_working_directory: str,
        initial_run_as_admin: bool,
        initial_wait: bool,
        initial_window_style: str,
    ) -> dict[str, object] | None:
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setModal(True)
        dialog.resize(520, 220)

        layout = QtWidgets.QVBoxLayout(dialog)
        form = QtWidgets.QFormLayout()
        layout.addLayout(form)

        arguments_edit = QtWidgets.QLineEdit()
        arguments_edit.setPlaceholderText('e.g. /silent /norestart or "--help"')
        arguments_edit.setText(initial_arguments)
        form.addRow("Arguments:", arguments_edit)

        workdir_row = QtWidgets.QHBoxLayout()
        workdir_edit = QtWidgets.QLineEdit()
        workdir_edit.setText(initial_working_directory)
        workdir_row.addWidget(workdir_edit, 1)

        browse_button = QtWidgets.QPushButton("...")
        browse_button.setFixedWidth(32)
        workdir_row.addWidget(browse_button)
        form.addRow("Working Directory:", workdir_row)

        is_windows = sys.platform == "win32"
        run_as_admin_checkbox = QtWidgets.QCheckBox("Run as Administrator")
        run_as_admin_checkbox.setChecked(initial_run_as_admin if is_windows else False)
        if is_windows:
            form.addRow("", run_as_admin_checkbox)

        wait_checkbox = QtWidgets.QCheckBox("Wait for completion")
        wait_checkbox.setChecked(initial_wait)
        form.addRow("", wait_checkbox)

        window_style_combo = NoWheelComboBox()
        window_style_combo.addItem("Normal", "normal")
        window_style_combo.addItem("Minimized", "minimized")
        window_style_combo.addItem("Maximized", "maximized")
        window_style_combo.addItem("Hidden", "hidden")
        initial_style = (initial_window_style or "normal").strip().lower()
        initial_index = max(0, window_style_combo.findData(initial_style))
        window_style_combo.setCurrentIndex(initial_index)
        if is_windows:
            form.addRow("Window Style:", window_style_combo)

        def choose_workdir() -> None:
            selected = QtWidgets.QFileDialog.getExistingDirectory(
                dialog,
                "Choose Working Directory",
                workdir_edit.text().strip() or str(Path.home()),
            )
            if selected:
                workdir_edit.setText(selected)

        browse_button.clicked.connect(choose_workdir)

        hint = QtWidgets.QLabel(
            "Note: Arguments are app-specific and are passed unchanged to the target application."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QtWidgets.QDialog.DialogCode.Accepted:
            return None

        return {
            "arguments": arguments_edit.text().strip(),
            "working_directory": workdir_edit.text().strip(),
            "run_as_admin": run_as_admin_checkbox.isChecked() if is_windows else False,
            "wait": wait_checkbox.isChecked(),
            "window_style": str(window_style_combo.currentData()) if is_windows else "normal",
        }

    def _default_working_directory_for_entry(self, entry: ToolboxEntry) -> str:
        path = Path(entry.path).expanduser()
        if path.exists() and path.is_dir():
            return str(path)
        return str(path.parent)

    def _entry_has_persistent_launch_options(self, entry: ToolboxEntry) -> bool:
        return bool(
            entry.launch_arguments.strip()
            or entry.launch_working_directory.strip()
            or entry.launch_wait
            or (
                sys.platform == "win32"
                and entry.launch_window_style.strip().lower() != "normal"
            )
        )

    def launch_selected(self, ctx: Optional[ToolboxTabContext] = None) -> None:
        ctx = ctx or self.current_toolbox_context()
        if ctx is None or not ctx.selected_ids:
            return
        first_entry = next(
            (
                entry
                for entry in ctx.entries
                if entry.entry_id in ctx.selected_ids and entry.is_tool
            ),
            None,
        )
        if first_entry is None:
            self.status.showMessage("Please select an app.", 3000)
            return
        self._launch_entry(ctx, first_entry)

    def _launch_entry(
        self, ctx: ToolboxTabContext, entry: ToolboxEntry, force_admin: Optional[bool] = None
    ) -> None:
        try:
            if sys.platform.startswith("linux") and Path(entry.path).suffix.lower() == ".desktop":
                if entry.launch_arguments.strip():
                    raise OSError(
                        "Custom launch arguments are not supported for Linux .desktop shortcuts."
                    )
                self.status.showMessage(f"Starting: {entry.title}", 3000)
                self.desktop_process_manager.launch(
                    entry.path,
                    working_directory=entry.launch_working_directory,
                )
                self._update_details(ctx)
                return
            run_as_admin = (
                entry.always_run_as_admin if force_admin is None else force_admin
            ) if sys.platform == "win32" else False
            window_style = (
                entry.launch_window_style if sys.platform == "win32" else "normal"
            )
            launch_path(
                entry.path,
                run_as_admin=run_as_admin,
                arguments=entry.launch_arguments,
                working_directory=entry.launch_working_directory,
                wait=entry.launch_wait,
                window_style=window_style,
            )
            self.status.showMessage(f"Launched: {entry.title}", 3000)
        except (FileNotFoundError, PermissionError, OSError, ValueError) as exc:
            logger.warning(
                "Failed to launch tool '%s': %s",
                self._entry_target_log_label(entry),
                exc,
            )
            QtWidgets.QMessageBox.critical(self, "Launch failed", str(exc))
            self.status.showMessage("Launch failed.", 3000)
        self._update_details(ctx)

    def _launch_entry_with_drop(
        self,
        ctx: ToolboxTabContext,
        entry: ToolboxEntry,
        launch_input: DesktopLaunchInput,
    ) -> None:
        try:
            if not (
                sys.platform.startswith("linux")
                and Path(entry.path).suffix.lower() == ".desktop"
            ):
                raise OSError("File drop is currently supported for Linux .desktop entries.")
            self.status.showMessage(
                f"Starting {len(launch_input.items)} dropped item(s): {entry.title}",
                3500,
            )
            prepared = prepare_desktop_launch(
                entry.path,
                launch_input=launch_input,
                working_directory=entry.launch_working_directory,
            )
            self.desktop_process_manager.launch_prepared(prepared)
            action = (
                "Launch request delegated for"
                if prepared.mode == "gio"
                else "Launched"
            )
            self.status.showMessage(
                f"{action} {len(launch_input.items)} dropped item(s): {entry.title}",
                4500 if prepared.mode == "gio" else 3500,
            )
        except (FileNotFoundError, PermissionError, OSError, ValueError) as exc:
            logger.warning(
                "Failed to launch dropped items with '%s': %s",
                self._entry_target_log_label(entry),
                exc,
            )
            QtWidgets.QMessageBox.critical(self, "Drop launch failed", str(exc))
            self.status.showMessage("Drop launch failed.", 3000)
        self._update_details(ctx)

    def _on_entry_files_dropped(
        self,
        ctx: ToolboxTabContext,
        entry_id: str,
        payload: object,
    ) -> None:
        entry = next(
            (
                item
                for item in ctx.entries
                if item.entry_id == entry_id and item.is_tool
            ),
            None,
        )
        if entry is None:
            self.status.showMessage("Drop target is no longer available.", 3000)
            return

        mime_database = QtCore.QMimeDatabase()
        launch_items: list[DesktopLaunchItem] = []
        if isinstance(payload, (tuple, list)):
            for raw_item in payload:
                if not isinstance(raw_item, dict):
                    continue
                url = str(raw_item.get("url") or "").strip()
                local_path = str(raw_item.get("local_path") or "").strip()
                mime_type = ""
                if local_path:
                    path = Path(local_path)
                    if path.is_dir():
                        mime_type = "inode/directory"
                    else:
                        mime_type = mime_database.mimeTypeForFile(local_path).name()
                if url or local_path:
                    launch_items.append(
                        DesktopLaunchItem(
                            url=url,
                            local_path=local_path,
                            mime_type=mime_type,
                        )
                    )
        if not launch_items:
            QtWidgets.QMessageBox.warning(
                self,
                "Drop rejected",
                "The drop did not contain a usable file or URL.",
            )
            return
        self._launch_entry_with_drop(
            ctx,
            entry,
            DesktopLaunchInput(tuple(launch_items)),
        )

    @QtCore.Slot(str, str)
    def _on_desktop_launch_started(self, _path: str, title: str) -> None:
        self.status.showMessage(f"Launched: {title}", 3000)

    @QtCore.Slot(str, str)
    def _on_desktop_launch_delegated(self, _path: str, title: str) -> None:
        self.status.showMessage(
            f"Launch request delegated to the desktop system: {title}",
            4000,
        )

    @QtCore.Slot(str, str, int)
    def _on_desktop_launch_finished(
        self,
        _path: str,
        title: str,
        _exit_code: int,
    ) -> None:
        self.status.showMessage(f"Completed: {title}", 2500)

    @QtCore.Slot(str, str, str, bool)
    def _on_desktop_launch_failed(
        self,
        path: str,
        title: str,
        message: str,
        show_dialog: bool,
    ) -> None:
        logger.warning(
            "Desktop launch failed for '%s' [%s]: %s",
            title,
            Path(path).name,
            message.splitlines()[0] if message else "unknown error",
        )
        self.status.showMessage(f"Launch failed: {title}", 4500)
        if show_dialog:
            QtWidgets.QMessageBox.critical(self, "Launch failed", message)

    def _launch_entry_with_options(self, ctx: ToolboxTabContext, entry: ToolboxEntry) -> None:
        options = self._prompt_launch_options(
            entry,
            title="Launch with Parameters",
            initial_arguments=entry.launch_arguments,
            initial_working_directory=entry.launch_working_directory
            or self._default_working_directory_for_entry(entry),
            initial_run_as_admin=entry.always_run_as_admin,
            initial_wait=entry.launch_wait,
            initial_window_style=entry.launch_window_style,
        )
        if options is None:
            return
        try:
            if (
                sys.platform.startswith("linux")
                and Path(entry.path).suffix.lower() == ".desktop"
            ):
                if str(options["arguments"]).strip():
                    raise OSError(
                        "Custom launch arguments are not supported for Linux .desktop shortcuts."
                    )
                self.status.showMessage(
                    f"Starting with options: {entry.title}",
                    3000,
                )
                self.desktop_process_manager.launch(
                    entry.path,
                    working_directory=str(options["working_directory"]),
                )
                self._update_details(ctx)
                return
            launch_path(
                entry.path,
                run_as_admin=bool(options["run_as_admin"]),
                arguments=str(options["arguments"]),
                working_directory=str(options["working_directory"]),
                wait=bool(options["wait"]),
                window_style=str(options["window_style"]),
            )
            self.status.showMessage(f"Launched with parameters: {entry.title}", 3000)
        except (FileNotFoundError, PermissionError, OSError, ValueError) as exc:
            logger.warning(
                "Failed to launch tool with options '%s': %s",
                self._entry_target_log_label(entry),
                exc,
            )
            QtWidgets.QMessageBox.critical(self, "Launch failed", str(exc))
            self.status.showMessage("Launch with parameters failed.", 3000)
        self._update_details(ctx)

    def _configure_persistent_launch_options(
        self, ctx: ToolboxTabContext, entry: ToolboxEntry
    ) -> None:
        options = self._prompt_launch_options(
            entry,
            title="Save Default Launch Options",
            initial_arguments=entry.launch_arguments,
            initial_working_directory=entry.launch_working_directory
            or self._default_working_directory_for_entry(entry),
            initial_run_as_admin=entry.always_run_as_admin,
            initial_wait=entry.launch_wait,
            initial_window_style=entry.launch_window_style,
        )
        if options is None:
            return

        entry.launch_arguments = str(options["arguments"]).strip()
        entry.launch_working_directory = str(options["working_directory"]).strip()
        entry.always_run_as_admin = (
            bool(options["run_as_admin"]) if sys.platform == "win32" else False
        )
        entry.launch_wait = bool(options["wait"])
        entry.launch_window_style = (
            str(options["window_style"]).strip().lower()
            if sys.platform == "win32"
            else "normal"
        ) or "normal"
        if entry.launch_window_style not in {"normal", "minimized", "maximized", "hidden"}:
            entry.launch_window_style = "normal"

        self.persist_toolbox_state()
        self._update_details(ctx)
        self.status.showMessage(f"Default launch options saved: {entry.title}", 3000)

    def _clear_persistent_launch_options(
        self, ctx: ToolboxTabContext, entry: ToolboxEntry
    ) -> None:
        entry.launch_arguments = ""
        entry.launch_working_directory = ""
        entry.always_run_as_admin = False
        entry.launch_wait = False
        entry.launch_window_style = "normal"
        self.persist_toolbox_state()
        self._update_details(ctx)
        self.status.showMessage(f"Default launch options reset: {entry.title}", 3000)

    def _open_entry_path(self, entry: ToolboxEntry) -> None:
        target = Path(entry.path).expanduser()
        open_target = target if target.is_dir() else target.parent
        if open_directory_in_os(str(open_target)):
            self.status.showMessage(f"Path opened: {open_target}", 3000)
            return
        QtWidgets.QMessageBox.warning(self, "Error", f"Could not open folder:\n{open_target}")
