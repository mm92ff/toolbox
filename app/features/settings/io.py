#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Settings persistence and snapshot I/O helpers for MainWindow."""

from __future__ import annotations

import logging
from pathlib import Path

from app import constants
from app.features.settings.io_importer import apply_imported_ui_settings
from app.features.settings.io_loader import load_settings
from app.features.settings.io_snapshot import (
    build_ui_settings_snapshot,
    persist_ui_settings_json,
    read_persisted_ui_settings,
    save_settings,
)
from app.services.json_io import read_json_utf8, write_json_utf8_atomic

logger = logging.getLogger(__name__)


class MainWindowSettingsIOMixin:
    @staticmethod
    def _normalize_settings_tab_title(value: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized in {"", "einstellungen", "settings"}:
            return "Settings"
        return value.strip()

    @staticmethod
    def _normalize_help_tab_title(value: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized in {"", "hilfe", "help"}:
            return "Help"
        return value.strip()

    def _build_ui_settings_snapshot(self) -> dict[str, object]:
        return build_ui_settings_snapshot(self)

    def _write_json_atomic(self, destination: Path, payload: dict[str, object]) -> None:
        write_json_utf8_atomic(destination, payload, ensure_ascii=False, indent=2)

    def _read_json_atomic(self, source: Path) -> dict[str, object] | list[object] | object:
        return read_json_utf8(source)

    def _ui_settings_json_path(self) -> Path:
        return self.config_dir / constants.UI_SETTINGS_FILENAME

    def _read_persisted_ui_settings(self) -> dict[str, object] | None:
        return read_persisted_ui_settings(self, logger)

    def _persist_ui_settings_json(self) -> None:
        persist_ui_settings_json(self)

    def _apply_imported_ui_settings(self, ui_settings: dict[str, object]) -> None:
        apply_imported_ui_settings(self, ui_settings)

    def _load_settings(self) -> None:
        load_settings(self)

    def _save_settings(self) -> None:
        save_settings(self, logger)

    def _set_slider_value(self, widget_name: str, value: int) -> None:
        slider = self.widgets[widget_name]
        slider.blockSignals(True)
        slider.setValue(value)
        slider.blockSignals(False)
