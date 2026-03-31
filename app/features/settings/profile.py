#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Import/export profile behavior for MainWindow settings."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from app import constants
from app.domain.models import ToolboxTabData
from app.services.json_io import read_json_utf8
from app.services.storage import save_toolbox_tabs


class MainWindowSettingsProfileMixin:
    @staticmethod
    def _default_primary_tab() -> ToolboxTabData:
        return ToolboxTabData(title=constants.DEFAULT_TOOLBOX_TAB_TITLE, entries=[], is_primary=True)

    @staticmethod
    def _parse_imported_tabs(raw_tabs: object) -> list[ToolboxTabData]:
        if not isinstance(raw_tabs, list):
            raise ValueError("Invalid file: 'toolbox_state.tabs' must be an array.")

        imported_tabs: list[ToolboxTabData] = []
        for index, raw_tab in enumerate(raw_tabs):
            if not isinstance(raw_tab, dict):
                raise ValueError(f"Invalid file: 'toolbox_state.tabs[{index}]' must be an object.")
            try:
                imported_tabs.append(ToolboxTabData.from_dict(raw_tab))
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Invalid file: malformed tab at 'toolbox_state.tabs[{index}]': {exc}"
                ) from exc
        if not imported_tabs:
            return [MainWindowSettingsProfileMixin._default_primary_tab()]
        return imported_tabs

    @staticmethod
    def _normalize_primary_tab(imported_tabs: list[ToolboxTabData]) -> None:
        if not any(tab.is_primary for tab in imported_tabs):
            imported_tabs[0].is_primary = True
            return
        first_primary = next(i for i, tab in enumerate(imported_tabs) if tab.is_primary)
        for i, tab in enumerate(imported_tabs):
            tab.is_primary = i == first_primary

    @staticmethod
    def _validate_profile_schema_version(payload: dict[str, object]) -> None:
        raw_version = payload.get("schema_version")
        if raw_version is None:
            return
        if not isinstance(raw_version, int):
            raise ValueError("Invalid file: 'schema_version' must be an integer.")
        if raw_version > 1:
            raise ValueError(
                f"Unsupported profile schema version: {raw_version}. "
                "Please export from a compatible Toolbox version."
            )

    @staticmethod
    def _validate_toolbox_state_version(toolbox_state: dict[str, object]) -> None:
        raw_version = toolbox_state.get("version")
        if raw_version is None:
            return
        if not isinstance(raw_version, int):
            raise ValueError("Invalid file: 'toolbox_state.version' must be an integer.")
        if raw_version > 3:
            raise ValueError(
                f"Unsupported toolbox state version: {raw_version}. "
                "Please import a compatible export file."
            )

    def _export_profile_json(self) -> None:
        suggested = f"{self.app_name}_toolbox_export.json"
        target_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export Toolbox Configuration",
            str(Path.home() / suggested),
            "JSON File (*.json)",
        )
        if not target_path:
            return
        destination = Path(target_path)
        if destination.suffix.lower() != ".json":
            destination = destination.with_suffix(".json")

        payload = {
            "schema_version": 1,
            "exported_at_utc": QtCore.QDateTime.currentDateTimeUtc().toString(
                QtCore.Qt.DateFormat.ISODate
            ),
            "application": self.app_name,
            "toolbox_state": {
                "version": 3,
                "tabs": [tab.to_dict() for tab in self._collect_toolbox_state()],
            },
            "ui_settings": self._build_ui_settings_snapshot(),
        }

        try:
            self._write_json_atomic(destination, payload)
        except OSError as exc:
            QtWidgets.QMessageBox.critical(self, "Export failed", str(exc))
            self.status.showMessage("Export failed.", 3000)
            return

        self.status.showMessage(f"Export successful: {destination}", 4000)

    def _import_profile_json(self) -> None:
        source_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Import Toolbox Configuration",
            str(Path.home()),
            "JSON File (*.json)",
        )
        if not source_path:
            return

        try:
            payload = read_json_utf8(Path(source_path))
        except (OSError, json.JSONDecodeError) as exc:
            QtWidgets.QMessageBox.critical(self, "Import failed", f"Could not read JSON:\n{exc}")
            self.status.showMessage("Import failed.", 3000)
            return

        if not isinstance(payload, dict):
            QtWidgets.QMessageBox.critical(
                self, "Import failed", "Invalid file: JSON root is not an object."
            )
            self.status.showMessage("Import failed.", 3000)
            return

        try:
            self._validate_profile_schema_version(payload)
        except ValueError as exc:
            QtWidgets.QMessageBox.critical(self, "Import failed", str(exc))
            self.status.showMessage("Import failed.", 3000)
            return

        toolbox_state = payload.get("toolbox_state")
        if not isinstance(toolbox_state, dict):
            QtWidgets.QMessageBox.critical(
                self, "Import failed", "Invalid file: 'toolbox_state' is missing."
            )
            self.status.showMessage("Import failed.", 3000)
            return

        try:
            self._validate_toolbox_state_version(toolbox_state)
            imported_tabs = self._parse_imported_tabs(toolbox_state.get("tabs"))
            self._normalize_primary_tab(imported_tabs)
        except ValueError as exc:
            QtWidgets.QMessageBox.critical(self, "Import failed", str(exc))
            self.status.showMessage("Import failed.", 3000)
            return

        try:
            save_toolbox_tabs(self.config_dir, imported_tabs)
            ui_settings = payload.get("ui_settings")
            if isinstance(ui_settings, dict):
                self._apply_imported_ui_settings(ui_settings)
                self._persist_ui_settings_json()
        except (OSError, ValueError, TypeError) as exc:
            QtWidgets.QMessageBox.critical(self, "Import failed", str(exc))
            self.status.showMessage("Import failed.", 3000)
            return

        self._clear_toolbox_tabs()
        self._load_toolbox_state()
        self._load_settings()
        self.refresh_all_canvases()
        self.status.showMessage("Import applied successfully.", 4000)
