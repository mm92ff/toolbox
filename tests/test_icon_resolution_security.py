from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtGui, QtWidgets

from app.services.linux_icon_theme import clear_linux_icon_cache, desktop_icon_for_path


def _app() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_icon_resolution_never_executes_target(tmp_path: Path) -> None:
    _app()
    marker = tmp_path / "executed"
    target = tmp_path / "unknown-executable"
    target.write_text(
        f"#!/bin/sh\ntouch {marker}\n",
        encoding="utf-8",
    )
    target.chmod(0o755)
    provider = QtWidgets.QFileIconProvider()
    fallback = QtGui.QIcon.fromTheme("application-x-executable")

    with patch("app.services.linux_icon_theme.subprocess.Popen") as popen:
        icon = desktop_icon_for_path(target, provider, fallback)

    popen.assert_not_called()
    assert not marker.exists()
    assert isinstance(icon, QtGui.QIcon)


def test_sidecar_icon_is_preferred_without_executing_target(tmp_path: Path) -> None:
    _app()
    target = tmp_path / "sample.AppImage"
    target.write_bytes(b"not an actual appimage")
    target.chmod(0o755)
    sidecar = tmp_path / "sample.png"
    pixmap = QtGui.QPixmap(32, 32)
    pixmap.fill(QtGui.QColor("#2288cc"))
    assert pixmap.save(str(sidecar), "PNG")

    with patch("app.services.linux_icon_theme.subprocess.Popen") as popen:
        icon = desktop_icon_for_path(target, QtWidgets.QFileIconProvider())

    popen.assert_not_called()
    assert icon.pixmap(32, 32).toImage().pixelColor(16, 16).name() == "#2288cc"


def test_sidecar_lookup_is_case_insensitive_and_invalidates_negative_cache(
    tmp_path: Path,
) -> None:
    _app()
    target = tmp_path / "Demo.AppImage"
    target.write_bytes(b"payload")
    provider = QtWidgets.QFileIconProvider()
    fallback = QtGui.QIcon()
    clear_linux_icon_cache()

    first = desktop_icon_for_path(target, provider, fallback)
    sidecar = tmp_path / "DEMO.PNG"
    pixmap = QtGui.QPixmap(24, 24)
    pixmap.fill(QtGui.QColor("#44aa66"))
    assert pixmap.save(str(sidecar), "PNG")
    second = desktop_icon_for_path(target, provider, fallback)

    assert isinstance(first, QtGui.QIcon)
    assert second.pixmap(24, 24).toImage().pixelColor(12, 12).name() == "#44aa66"


def test_appimage_cache_miss_schedules_background_static_extraction(tmp_path: Path) -> None:
    _app()
    target = tmp_path / "New.AppImage"
    target.write_bytes(b"not a squashfs payload")
    provider = QtWidgets.QFileIconProvider()
    service = MagicMock()

    desktop_icon_for_path(
        target,
        provider,
        QtGui.QIcon(),
        service,
    )

    service.request.assert_called_once_with(target)
