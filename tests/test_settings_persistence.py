from __future__ import annotations

import os
import uuid
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets

from app import constants
from app.features.settings.schema import SETTING_SPECS
from app.main_window import MainWindow


def _create_window(app_name: str, config_dir: Path) -> MainWindow:
    with patch.object(
        QtWidgets.QSystemTrayIcon,
        "isSystemTrayAvailable",
        return_value=False,
    ):
        return MainWindow(app_name, config_dir=config_dir)


def test_schema_keys_survive_real_qsettings_restart(tmp_path: Path) -> None:
    app_name = f"ToolboxSettings-{uuid.uuid4().hex}"
    config_dir = tmp_path / "config"
    first = _create_window(app_name, config_dir)
    settings = QtCore.QSettings()
    settings.clear()
    try:
        first.widgets[constants.WIDGET_SHOW_TOOLTIPS_CHECKBOX].setChecked(False)
        first.widgets[constants.WIDGET_FOLDER_SHOW_FILE_COUNT_CHECKBOX].setChecked(True)
        first.widgets[constants.WIDGET_FILE_ASSOC_USE_SYSTEM_CHECKBOX].setChecked(False)
        first.widgets[constants.WIDGET_FILE_ASSOC_AUDIO_INPUT].setText(
            "flatpak run org.videolan.VLC"
        )
        first._apply_pending_settings()
        first._force_quit = True
        first.close()

        second = _create_window(app_name, config_dir)
        try:
            assert second.current_show_tooltips() is False
            assert second.current_folder_show_file_count() is True
            assert second.current_file_assoc_use_system() is False
            assert second.current_file_assoc_audio() == "flatpak run org.videolan.VLC"
        finally:
            second._force_quit = True
            second.close()
    finally:
        QtCore.QSettings().clear()


def test_every_schema_field_has_one_unique_qsettings_key() -> None:
    keys = [spec.qsettings_key for spec in SETTING_SPECS]

    assert len(keys) == len(set(keys))
    assert "interaction/show_tooltips" in keys
    assert "system/folder_show_file_count" in keys
    assert {
        "system/file_assoc_use_system",
        "system/file_assoc_audio",
        "system/file_assoc_video",
        "system/file_assoc_image",
        "system/file_assoc_pdf",
        "system/file_assoc_document",
    }.issubset(keys)


def test_reverting_file_association_widgets_clears_dirty_state(tmp_path: Path) -> None:
    app_name = f"ToolboxDirty-{uuid.uuid4().hex}"
    window = _create_window(app_name, tmp_path / "config")
    try:
        for widget_name in (
            constants.WIDGET_FILE_ASSOC_AUDIO_INPUT,
            constants.WIDGET_FILE_ASSOC_VIDEO_INPUT,
            constants.WIDGET_FILE_ASSOC_IMAGE_INPUT,
            constants.WIDGET_FILE_ASSOC_PDF_INPUT,
            constants.WIDGET_FILE_ASSOC_DOCUMENT_INPUT,
        ):
            widget = window.widgets[widget_name]
            original = widget.text()
            widget.setText("temporary-command")
            assert window._settings_dirty is True
            widget.setText(original)
            assert window._settings_dirty is False
    finally:
        window._force_quit = True
        window.close()
        QtCore.QSettings().clear()
