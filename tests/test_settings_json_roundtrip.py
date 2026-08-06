from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PySide6 import QtCore, QtGui

from app import constants
from app.features.settings import io_importer as io_importer_module
from app.features.settings import profile as profile_module
from app.features.settings.io_snapshot import build_ui_settings_snapshot
from app.features.settings.profile import MainWindowSettingsProfileMixin


class _FakeByteArray:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def toBase64(self) -> bytes:  # noqa: N802 - Qt naming style
        return QtCore.QByteArray(self._payload).toBase64().data()


class _FakeTabWidget:
    def __init__(self, index: int) -> None:
        self._index = index

    def currentIndex(self) -> int:  # noqa: N802 - Qt naming style
        return self._index


class _FakeSplitter:
    def __init__(self, sizes: list[int]) -> None:
        self._sizes = sizes

    def sizes(self) -> list[int]:
        return list(self._sizes)


@dataclass
class _FakeTabContext:
    tab_id: str
    splitter: _FakeSplitter


class _SnapshotOwner:
    def __init__(self) -> None:
        self.tab_widget = _FakeTabWidget(index=2)
        self._settings_title = "Settings"
        self._help_title = "Help"
        self._hidden_toolbox_tab_ids = {"tab_hidden"}
        self._help_tab_hidden = True
        self.toolbox_tabs = [
            _FakeTabContext(tab_id="tab_a", splitter=_FakeSplitter([220, 640, 150])),
            _FakeTabContext(tab_id="tab_b", splitter=_FakeSplitter([500])),
        ]

    def saveGeometry(self) -> _FakeByteArray:
        return _FakeByteArray(b"geometry-bytes")

    def width(self) -> int:
        return 1280

    def height(self) -> int:
        return 780

    def current_icon_size(self) -> int:
        return 84

    def current_tile_frame_enabled(self) -> bool:
        return True

    def current_image_file_preview_enabled(self) -> bool:
        return True

    def current_image_file_preview_mode(self) -> str:
        return constants.IMAGE_PREVIEW_MODE_FILL

    def current_preview_overlay_enabled(self) -> bool:
        return True

    def current_video_file_preview_enabled(self) -> bool:
        return True

    def current_hover_preview_enabled(self) -> bool:
        return False

    def current_ffmpeg_manual_path(self) -> str:
        return r"C:\Tools\ffmpeg\ffmpeg.exe"

    def current_icon_preview_background_color(self) -> str:
        return "#3a4b5c"

    def current_tile_frame_thickness(self) -> int:
        return 3

    def current_tile_frame_color(self) -> str:
        return "#111111"

    def current_tile_highlight_color(self) -> str:
        return "#222222"

    def current_grid_spacing_x(self) -> int:
        return 7

    def current_grid_spacing_y(self) -> int:
        return 9

    def current_auto_compact_left(self) -> bool:
        return True

    def current_section_font_size(self) -> int:
        return 17

    def current_section_line_thickness(self) -> int:
        return 4

    def current_section_gap_above(self) -> int:
        return 6

    def current_section_gap_below(self) -> int:
        return 8

    def current_section_gap(self) -> int:
        return 8

    def current_section_line_color(self) -> str:
        return "#444a57"

    def current_tool_launch_mode(self) -> str:
        return constants.LAUNCH_CLICK_MODE_SINGLE

    def current_file_assoc_use_system(self) -> bool:
        return True

    def current_file_assoc_audio(self) -> str:
        return ""

    def current_file_assoc_video(self) -> str:
        return ""

    def current_file_assoc_image(self) -> str:
        return ""

    def current_file_assoc_pdf(self) -> str:
        return ""

    def current_file_assoc_document(self) -> str:
        return ""

    def current_folder_single_click_browse(self) -> bool:
        return False


class _FakeQSettings:
    def __init__(self) -> None:
        self.values: dict[str, Any] = {}

    def setValue(self, key: str, value: Any) -> None:  # noqa: N802 - Qt naming style
        self.values[key] = value

    def sync(self) -> None:
        return None


class _ImporterOwner:
    @staticmethod
    def _coerce_int(value: object, default: int) -> int:
        try:
            return int(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _coerce_str_list(value: object) -> list[str]:
        if isinstance(value, str):
            text = value.strip()
            return [text] if text else []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return []

    @staticmethod
    def _normalize_settings_tab_title(value: str) -> str:
        return (value or "").strip() or "Settings"

    @staticmethod
    def _normalize_help_tab_title(value: str) -> str:
        return (value or "").strip() or "Help"

    @staticmethod
    def _normalize_image_file_preview_mode(value: str) -> str:
        mode = (value or "").strip().lower()
        if mode == constants.IMAGE_PREVIEW_MODE_FILL:
            return constants.IMAGE_PREVIEW_MODE_FILL
        return constants.IMAGE_PREVIEW_MODE_FIT

    @staticmethod
    def _normalize_ffmpeg_manual_path(value: str) -> str:
        return (value or "").strip().strip('"')

    @staticmethod
    def _normalize_icon_preview_background_color(value: str) -> str:
        color = QtGui.QColor((value or "").strip())
        if not color.isValid():
            return constants.DEFAULT_ICON_PREVIEW_BACKGROUND_COLOR
        return color.name()

    @staticmethod
    def _normalize_tool_launch_mode(value: str) -> str:
        if (value or "").strip().lower() == constants.LAUNCH_CLICK_MODE_SINGLE:
            return constants.LAUNCH_CLICK_MODE_SINGLE
        return constants.LAUNCH_CLICK_MODE_DOUBLE

    @staticmethod
    def _default_tile_frame_color() -> str:
        return "#111111"

    @staticmethod
    def _default_tile_highlight_color() -> str:
        return "#222222"

    @staticmethod
    def width() -> int:
        return 1024

    @staticmethod
    def height() -> int:
        return 768


class _StatusSink:
    def __init__(self) -> None:
        self.messages: list[tuple[str, int]] = []

    def showMessage(self, text: str, timeout: int) -> None:  # noqa: N802 - Qt naming style
        self.messages.append((text, timeout))


class _ProfileHarness(MainWindowSettingsProfileMixin):
    def __init__(self) -> None:
        self.app_name = "toolbox"
        self.config_dir = Path(".")
        self.status = _StatusSink()
        self.applied_ui_settings: dict[str, object] | None = None
        self.persisted_ui_json = False
        self.cleared_tabs = False
        self.loaded_toolbox_state = False
        self.loaded_settings = False
        self.refreshed_canvases = False

    def _apply_imported_ui_settings(self, ui_settings: dict[str, object]) -> None:
        self.applied_ui_settings = ui_settings

    def _persist_ui_settings_json(self) -> None:
        self.persisted_ui_json = True

    def _clear_toolbox_tabs(self) -> None:
        self.cleared_tabs = True

    def _load_toolbox_state(self) -> None:
        self.loaded_toolbox_state = True

    def _load_settings(self) -> None:
        self.loaded_settings = True

    def refresh_all_canvases(self) -> None:
        self.refreshed_canvases = True


def test_build_ui_settings_snapshot_contains_all_layout_and_interaction_fields() -> None:
    owner = _SnapshotOwner()
    snapshot = build_ui_settings_snapshot(owner)

    layout = snapshot["layout"]
    assert set(layout.keys()) == {
        "icon_size",
        "tile_frame_enabled",
        "image_file_preview_enabled",
        "image_file_preview_mode",
        "preview_overlay_enabled",
        "video_file_preview_enabled",
        "hover_preview_enabled",
        "ffmpeg_manual_path",
        "icon_preview_background_color",
        "tile_frame_thickness",
        "tile_frame_color",
        "tile_highlight_color",
        "grid_spacing_x",
        "grid_spacing_y",
        "auto_compact_left",
        "section_font_size",
        "section_line_thickness",
        "section_gap_above",
        "section_gap_below",
        "section_gap",
        "section_line_color",
    }
    assert snapshot["interaction"] == {"tool_launch_mode": constants.LAUNCH_CLICK_MODE_SINGLE}
    system = snapshot["system"]
    assert system["minimize_to_tray"] is False
    assert system["file_assoc_use_system"] is True
    assert system["file_assoc_audio"] == ""
    assert system["folder_single_click_browse"] is False
    assert snapshot["tabs"]["hidden_toolbox_tab_ids"] == ["tab_hidden"]
    assert snapshot["toolbox_splitter_sizes"]["tab_a"] == [220, 640, 150]


def test_apply_imported_ui_settings_roundtrip_restores_all_keys(monkeypatch) -> None:
    settings_store = _FakeQSettings()
    owner = _ImporterOwner()
    snapshot = build_ui_settings_snapshot(_SnapshotOwner())

    monkeypatch.setattr(io_importer_module.QtCore, "QSettings", lambda: settings_store)

    io_importer_module.apply_imported_ui_settings(owner, snapshot)

    assert settings_store.values["tabs/current_index"] == 2
    assert settings_store.values["tabs/settings_title"] == "Settings"
    assert settings_store.values["tabs/help_title"] == "Help"
    assert settings_store.values["tabs/hidden_toolbox_tab_ids"] == ["tab_hidden"]
    assert settings_store.values["tabs/help_tab_hidden"] is True

    assert settings_store.values["layout/icon_size"] == 84
    assert settings_store.values["layout/tile_frame_enabled"] is True
    assert settings_store.values["layout/image_file_preview_enabled"] is True
    assert settings_store.values["layout/image_file_preview_mode"] == constants.IMAGE_PREVIEW_MODE_FILL
    assert settings_store.values["layout/video_file_preview_enabled"] is True
    assert settings_store.values["layout/hover_preview_enabled"] is False
    assert settings_store.values["layout/ffmpeg_manual_path"] == r"C:\Tools\ffmpeg\ffmpeg.exe"
    assert settings_store.values["layout/icon_preview_background_color"] == "#3a4b5c"
    assert settings_store.values["layout/tile_frame_thickness"] == 3
    assert settings_store.values["layout/tile_frame_color"] == "#111111"
    assert settings_store.values["layout/tile_highlight_color"] == "#222222"
    assert settings_store.values["layout/grid_spacing_x"] == 7
    assert settings_store.values["layout/grid_spacing_y"] == 9
    assert settings_store.values["layout/auto_compact_left"] is True
    assert settings_store.values["layout/section_font_size"] == 17
    assert settings_store.values["layout/section_line_thickness"] == 4
    assert settings_store.values["layout/section_gap_above"] == 6
    assert settings_store.values["layout/section_gap_below"] == 8
    assert settings_store.values["layout/section_gap"] == 8
    assert settings_store.values["layout/section_line_color"] == "#444a57"
    assert settings_store.values["interaction/tool_launch_mode"] == constants.LAUNCH_CLICK_MODE_SINGLE
    assert settings_store.values["system/file_assoc_use_system"] is True
    assert settings_store.values["system/file_assoc_audio"] == ""
    assert settings_store.values["system/file_assoc_pdf"] == ""
    assert settings_store.values["system/folder_single_click_browse"] is False
    assert settings_store.values["toolbox/tab_a/splitter_sizes"] == [220, 640, 150]
    assert settings_store.values["toolbox/tab_b/splitter_sizes"] == [500]


def test_profile_import_restores_toolbox_and_ui_settings(monkeypatch) -> None:
    harness = _ProfileHarness()
    captured_saved_tabs: list[object] = []
    payload = {
        "schema_version": 1,
        "toolbox_state": {
            "version": 3,
            "tabs": [
                {
                    "id": "tab-1",
                    "title": "Toolbox",
                    "is_primary": True,
                    "background_color": "#350022",
                    "entries": [
                        {
                            "id": "sec-1",
                            "title": "Section A",
                            "kind": "section",
                            "path": "",
                            "x": 20,
                            "y": 80,
                            "always_run_as_admin": False,
                            "launch_arguments": "",
                            "launch_working_directory": "",
                            "launch_wait": False,
                            "launch_window_style": "normal",
                            "section_line_color": "#00ff00",
                            "section_title_color": "#ffee00",
                        },
                        {
                            "id": "tool-1",
                            "title": "App",
                            "kind": "tool",
                            "path": r"C:\Tools\App.exe",
                            "x": 20,
                            "y": 180,
                            "always_run_as_admin": True,
                            "launch_arguments": "--demo",
                            "launch_working_directory": r"C:\Tools",
                            "launch_wait": True,
                            "launch_window_style": "minimized",
                        },
                    ],
                }
            ],
        },
        "ui_settings": {
            "layout": {
                "icon_size": 77,
                "ffmpeg_manual_path": r"C:\FFmpeg\ffmpeg.exe",
            }
        },
    }

    monkeypatch.setattr(
        profile_module.QtWidgets.QFileDialog,
        "getOpenFileName",
        lambda *_args, **_kwargs: ("dummy.json", "JSON"),
    )
    monkeypatch.setattr(profile_module, "read_json_utf8", lambda _path: payload)
    monkeypatch.setattr(
        profile_module,
        "save_toolbox_tabs",
        lambda _config_dir, tabs: captured_saved_tabs.extend(tabs),
    )

    harness._import_profile_json()

    assert len(captured_saved_tabs) == 1
    imported_tab = captured_saved_tabs[0]
    assert imported_tab.background_color == "#350022"
    assert imported_tab.entries[0].section_line_color == "#00ff00"
    assert imported_tab.entries[0].section_title_color == "#ffee00"
    assert imported_tab.entries[1].always_run_as_admin is True
    assert imported_tab.entries[1].launch_arguments == "--demo"
    assert imported_tab.entries[1].launch_working_directory == r"C:\Tools"
    assert imported_tab.entries[1].launch_wait is True
    assert imported_tab.entries[1].launch_window_style == "minimized"

    assert harness.applied_ui_settings == payload["ui_settings"]
    assert harness.persisted_ui_json is True
    assert harness.cleared_tabs is True
    assert harness.loaded_toolbox_state is True
    assert harness.loaded_settings is True
    assert harness.refreshed_canvases is True
