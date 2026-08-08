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
from app.features.settings.io_loader import _coerce_responsive_layout


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
        first.widgets[constants.WIDGET_SHOW_TRAY_ICON_CHECKBOX].setChecked(False)
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
            assert second.current_show_tray_icon() is False
            assert second.current_minimize_to_tray() is False
            assert not second.widgets[
                constants.WIDGET_MINIMIZE_TO_TRAY_CHECKBOX
            ].isEnabled()
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
    assert "system/show_tray_icon" in keys
    assert "system/minimize_to_tray" in keys
    assert "system/folder_show_file_count" in keys
    assert {
        "system/file_assoc_use_system",
        "system/file_assoc_audio",
        "system/file_assoc_video",
        "system/file_assoc_image",
        "system/file_assoc_pdf",
        "system/file_assoc_document",
    }.issubset(keys)


def test_old_profile_without_tile_font_keys_keeps_automatic_scaling(
    tmp_path: Path,
) -> None:
    app_name = f"ToolboxFontMigration-{uuid.uuid4().hex}"
    app = QtWidgets.QApplication.instance()
    assert app is not None
    app.setOrganizationName(app_name)
    app.setApplicationName(app_name)
    settings = QtCore.QSettings()
    settings.clear()
    settings.setValue("layout/icon_size", constants.MAX_ICON_SIZE)
    settings.sync()

    window = _create_window(app_name, tmp_path / "config")
    try:
        assert window.current_tile_font_auto() is True
        assert window.current_tile_font_size() == constants.DEFAULT_TILE_FONT_SIZE
        assert not window.widgets[constants.WIDGET_TILE_FONT_SIZE_SLIDER].isEnabled()
    finally:
        window._force_quit = True
        window.close()
        QtCore.QSettings().clear()


def test_old_profile_without_responsive_key_migrates_to_enabled_layout(tmp_path: Path) -> None:
    app_name = f"ToolboxResponsiveMigration-{uuid.uuid4().hex}"
    app = QtWidgets.QApplication.instance()
    assert app is not None
    app.setOrganizationName(app_name)
    app.setApplicationName(app_name)
    settings = QtCore.QSettings()
    settings.clear()
    settings.setValue("layout/icon_size", constants.DEFAULT_ICON_SIZE)
    settings.sync()

    window = _create_window(app_name, tmp_path / "config")
    try:
        assert window.current_responsive_toolbox_layout() is True
        assert window.toolbox_tabs[0].canvas.responsive_layout_enabled() is True
    finally:
        window._force_quit = True
        window.close()
        QtCore.QSettings().clear()


def test_invalid_local_responsive_setting_uses_safe_default() -> None:
    assert _coerce_responsive_layout("invalid") is True
    assert _coerce_responsive_layout(None) is True
    assert _coerce_responsive_layout("false") is False
    assert _coerce_responsive_layout("true") is True


def test_responsive_layout_can_be_disabled_after_default_migration(tmp_path: Path) -> None:
    app_name = f"ToolboxResponsiveChoice-{uuid.uuid4().hex}"
    config_dir = tmp_path / "config"
    first = _create_window(app_name, config_dir)
    try:
        assert first.current_responsive_toolbox_layout() is True
        first.widgets[
            constants.WIDGET_RESPONSIVE_TOOLBOX_LAYOUT_CHECKBOX
        ].setChecked(False)
        first._apply_pending_settings()
    finally:
        first._force_quit = True
        first.close()

    second = _create_window(app_name, config_dir)
    try:
        assert second.current_responsive_toolbox_layout() is False
        assert second.toolbox_tabs[0].canvas.responsive_layout_enabled() is False
    finally:
        second._force_quit = True
        second.close()
        QtCore.QSettings().clear()


def test_old_profile_without_tray_visibility_key_restores_visible_icon_default(
    tmp_path: Path,
) -> None:
    app_name = f"ToolboxTrayMigration-{uuid.uuid4().hex}"
    app = QtWidgets.QApplication.instance()
    assert app is not None
    app.setOrganizationName(app_name)
    app.setApplicationName(app_name)
    settings = QtCore.QSettings()
    settings.clear()
    settings.setValue("system/minimize_to_tray", False)
    settings.sync()

    window = _create_window(app_name, tmp_path / "config")
    try:
        assert window.current_show_tray_icon() is True
        assert window.current_minimize_to_tray() is False
        assert window.widgets[constants.WIDGET_SHOW_TRAY_ICON_CHECKBOX].isChecked()
        assert window.widgets[constants.WIDGET_MINIMIZE_TO_TRAY_CHECKBOX].isEnabled()
    finally:
        window._force_quit = True
        window.close()
        QtCore.QSettings().clear()


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
