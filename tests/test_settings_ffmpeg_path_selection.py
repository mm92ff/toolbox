import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets

from app import constants
from app.features.settings import appearance as appearance_module
from app.features.settings.appearance import MainWindowSettingsAppearanceMixin
from app.features.settings.state import MainWindowSettingsStateMixin
from app.services.video_thumbnails import FFMPEG_SOURCE_MANUAL, FfmpegResolution


def _ensure_app() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


class _StatusSink:
    def __init__(self) -> None:
        self.messages: list[tuple[str, int]] = []

    def showMessage(self, message: str, timeout_ms: int) -> None:  # noqa: N802 - Qt style
        self.messages.append((message, timeout_ms))


class _SettingsHarness(
    QtWidgets.QWidget,
    MainWindowSettingsAppearanceMixin,
    MainWindowSettingsStateMixin,
):
    def __init__(self) -> None:
        super().__init__()
        self.widgets: dict[str, QtWidgets.QWidget] = {}
        self.status = _StatusSink()
        self._settings_dirty = False

        manual_input = QtWidgets.QLineEdit()
        source_value = QtWidgets.QLabel()
        resolved_value = QtWidgets.QLabel()

        self.widgets[constants.WIDGET_FFMPEG_MANUAL_PATH_INPUT] = manual_input
        self.widgets[constants.WIDGET_FFMPEG_SOURCE_VALUE] = source_value
        self.widgets[constants.WIDGET_FFMPEG_RESOLVED_PATH_VALUE] = resolved_value

    def _mark_settings_dirty(self) -> None:
        self._settings_dirty = True


def test_update_ffmpeg_status_preview_uses_normalized_manual_path(monkeypatch) -> None:
    _ensure_app()
    harness = _SettingsHarness()
    harness.widgets[constants.WIDGET_FFMPEG_MANUAL_PATH_INPUT].setText(
        '  "C:\\Tools\\ffmpeg\\ffmpeg.exe"  '
    )
    received: dict[str, str | None] = {}

    def _fake_resolve(manual_path: str | None) -> FfmpegResolution:
        received["manual_path"] = manual_path
        return FfmpegResolution(
            path=r"C:\Tools\ffmpeg\ffmpeg.exe",
            source=FFMPEG_SOURCE_MANUAL,
        )

    monkeypatch.setattr(appearance_module, "resolve_ffmpeg_path", _fake_resolve)

    harness._update_ffmpeg_status_preview()

    assert received["manual_path"] == r"C:\Tools\ffmpeg\ffmpeg.exe"
    assert (
        harness.widgets[constants.WIDGET_FFMPEG_SOURCE_VALUE].text()
        == "Manual path (Settings)"
    )
    assert (
        harness.widgets[constants.WIDGET_FFMPEG_RESOLVED_PATH_VALUE].text()
        == r"C:\Tools\ffmpeg\ffmpeg.exe"
    )


def test_on_ffmpeg_manual_path_changed_normalizes_and_marks_dirty(monkeypatch) -> None:
    _ensure_app()
    harness = _SettingsHarness()
    harness.widgets[constants.WIDGET_FFMPEG_MANUAL_PATH_INPUT].setText(
        ' "C:\\Portable\\ffmpeg.exe" '
    )
    calls = {"cache_clear": 0, "status_update": 0}

    monkeypatch.setattr(
        appearance_module,
        "clear_ffmpeg_resolution_cache",
        lambda: calls.__setitem__("cache_clear", calls["cache_clear"] + 1),
    )
    monkeypatch.setattr(
        harness,
        "_update_ffmpeg_status_preview",
        lambda: calls.__setitem__("status_update", calls["status_update"] + 1),
    )

    harness._on_ffmpeg_manual_path_changed()

    assert (
        harness.widgets[constants.WIDGET_FFMPEG_MANUAL_PATH_INPUT].text()
        == r"C:\Portable\ffmpeg.exe"
    )
    assert calls["cache_clear"] == 1
    assert calls["status_update"] == 1
    assert harness._settings_dirty is True


def test_choose_ffmpeg_manual_path_updates_input_and_triggers_change(monkeypatch) -> None:
    _ensure_app()
    harness = _SettingsHarness()
    expected_path = r"C:\Custom\ffmpeg.exe"
    calls = {"changed": 0}

    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getOpenFileName",
        lambda *_args, **_kwargs: (expected_path, "Executable"),
    )
    monkeypatch.setattr(
        harness,
        "_on_ffmpeg_manual_path_changed",
        lambda: calls.__setitem__("changed", calls["changed"] + 1),
    )

    harness._choose_ffmpeg_manual_path()

    assert harness.widgets[constants.WIDGET_FFMPEG_MANUAL_PATH_INPUT].text() == expected_path
    assert calls["changed"] == 1


def test_choose_ffmpeg_manual_path_keeps_value_when_cancelled(monkeypatch) -> None:
    _ensure_app()
    harness = _SettingsHarness()
    harness.widgets[constants.WIDGET_FFMPEG_MANUAL_PATH_INPUT].setText(r"C:\Keep\ffmpeg.exe")
    calls = {"changed": 0}

    monkeypatch.setattr(
        QtWidgets.QFileDialog,
        "getOpenFileName",
        lambda *_args, **_kwargs: ("", ""),
    )
    monkeypatch.setattr(
        harness,
        "_on_ffmpeg_manual_path_changed",
        lambda: calls.__setitem__("changed", calls["changed"] + 1),
    )

    harness._choose_ffmpeg_manual_path()

    assert (
        harness.widgets[constants.WIDGET_FFMPEG_MANUAL_PATH_INPUT].text()
        == r"C:\Keep\ffmpeg.exe"
    )
    assert calls["changed"] == 0

