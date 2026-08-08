from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets

from app import constants
from app.main_window import MainWindow


def _ensure_app() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_tabs_and_layout_settings_survive_full_window_restart() -> None:
    _ensure_app()
    app_name = f"ToolboxLinuxPersistence_{uuid.uuid4().hex}"

    with tempfile.TemporaryDirectory() as temp_dir:
        config_dir = Path(temp_dir) / "toolbox"
        first = MainWindow(app_name, config_dir=config_dir)
        try:
            first._create_toolbox_tab("Persisted Linux tab", entries=[], is_primary=False)
            slider: QtWidgets.QSlider = first.widgets[constants.WIDGET_ICON_SIZE_SLIDER]  # type: ignore[assignment]
            target_icon_size = min(slider.maximum(), slider.value() + 9)
            if target_icon_size == slider.value():
                target_icon_size = max(slider.minimum(), slider.value() - 9)
            slider.setValue(target_icon_size)
            auto_font: QtWidgets.QCheckBox = first.widgets[
                constants.WIDGET_TILE_FONT_AUTO_CHECKBOX
            ]  # type: ignore[assignment]
            font_slider: QtWidgets.QSlider = first.widgets[
                constants.WIDGET_TILE_FONT_SIZE_SLIDER
            ]  # type: ignore[assignment]
            auto_font.setChecked(False)
            font_slider.setValue(21)
            responsive_checkbox: QtWidgets.QCheckBox = first.widgets[
                constants.WIDGET_RESPONSIVE_TOOLBOX_LAYOUT_CHECKBOX
            ]  # type: ignore[assignment]
            responsive_checkbox.setChecked(True)
            first._apply_pending_settings()
            first.persist_toolbox_state()
            first._save_settings()
        finally:
            first.close()

        second = MainWindow(app_name, config_dir=config_dir)
        try:
            assert any(
                context.title == "Persisted Linux tab"
                for context in second.toolbox_tabs
            )
            assert second.current_icon_size() == target_icon_size
            assert second.current_tile_font_auto() is False
            assert second.current_tile_font_size() == 21
            assert second.current_responsive_toolbox_layout() is True
            assert second.toolbox_tabs[0].canvas.responsive_layout_enabled() is True
            assert second.widgets[constants.WIDGET_TILE_FONT_SIZE_SLIDER].isEnabled()
            assert (config_dir / constants.TOOL_CONFIG_FILENAME).is_file()
            assert (config_dir / constants.UI_SETTINGS_FILENAME).is_file()
        finally:
            second.close()

    settings = QtCore.QSettings()
    settings.clear()
    settings.sync()
