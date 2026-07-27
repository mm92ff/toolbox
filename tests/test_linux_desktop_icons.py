from __future__ import annotations

import os
from pathlib import Path
import time
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtGui, QtWidgets

from app.services.linux_icon_theme import (
    clear_linux_icon_cache,
    desktop_icon_for_path,
    detect_linux_icon_theme,
    initialize_linux_icon_theme,
    linux_icon_theme_search_paths,
)


def _app() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _write_png(path: Path, color: str) -> Path:
    _app()
    pixmap = QtGui.QPixmap(64, 64)
    pixmap.fill(QtGui.QColor(color))
    assert pixmap.save(str(path), "PNG")
    return path


def _write_desktop(path: Path, icon: str) -> Path:
    path.write_text(
        (
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=Icon Test\n"
            "Exec=/usr/bin/true\n"
            f"Icon={icon}\n"
        ),
        encoding="utf-8",
    )
    return path


def test_icon_theme_search_paths_include_xdg_locations(tmp_path: Path) -> None:
    home = tmp_path / "home"
    environment = {
        "XDG_DATA_HOME": str(tmp_path / "user-data"),
        "XDG_DATA_DIRS": f"{tmp_path / 'one'}:{tmp_path / 'two'}",
    }

    paths = linux_icon_theme_search_paths(environment, home=home)

    assert str(tmp_path / "user-data" / "icons") in paths
    assert str(tmp_path / "one" / "icons") in paths
    assert str(tmp_path / "two" / "icons") in paths
    assert "/usr/share/icons" in paths


def test_detect_theme_prefers_existing_qt_theme() -> None:
    _app()
    old_theme = QtGui.QIcon.themeName()
    try:
        QtGui.QIcon.setThemeName("AlreadyConfigured")
        with patch(
            "app.services.linux_icon_theme._read_gsettings_value"
        ) as gsettings:
            assert detect_linux_icon_theme() == "AlreadyConfigured"
        gsettings.assert_not_called()
    finally:
        QtGui.QIcon.setThemeName(old_theme)


def test_detect_theme_uses_cinnamon_then_hicolor() -> None:
    _app()
    old_theme = QtGui.QIcon.themeName()
    try:
        QtGui.QIcon.setThemeName("")
        with patch(
            "app.services.linux_icon_theme._read_gsettings_value",
            side_effect=["Mint-Y-Sand"],
        ):
            assert detect_linux_icon_theme() == "Mint-Y-Sand"
        with patch(
            "app.services.linux_icon_theme._read_gsettings_value",
            return_value="",
        ):
            assert detect_linux_icon_theme() == "hicolor"
    finally:
        QtGui.QIcon.setThemeName(old_theme)


def test_desktop_icon_uses_absolute_icon_path(tmp_path: Path) -> None:
    _app()
    icon_path = _write_png(tmp_path / "absolute.png", "#33aa55")
    desktop = _write_desktop(tmp_path / "Absolute.desktop", str(icon_path))
    provider = QtWidgets.QFileIconProvider()

    icon = desktop_icon_for_path(desktop, provider)

    assert not icon.isNull()
    image = icon.pixmap(64, 64).toImage()
    assert image.pixelColor(32, 32).name() == "#33aa55"


def test_missing_absolute_icon_falls_back_to_file_provider(tmp_path: Path) -> None:
    _app()
    desktop = _write_desktop(
        tmp_path / "Missing.desktop",
        str(tmp_path / "does-not-exist.png"),
    )
    fallback_path = _write_png(tmp_path / "fallback.png", "#aa3355")
    provider = QtWidgets.QFileIconProvider()
    fallback = QtGui.QIcon(str(fallback_path))

    with patch.object(provider, "icon", return_value=fallback) as provider_icon:
        icon = desktop_icon_for_path(desktop, provider)

    provider_icon.assert_called_once()
    assert icon.pixmap(64, 64).toImage().pixelColor(32, 32).name() == "#aa3355"


def test_desktop_icon_cache_invalidates_when_icon_value_changes(
    tmp_path: Path,
) -> None:
    _app()
    first_path = _write_png(tmp_path / "first.png", "#bb4422")
    second_path = _write_png(tmp_path / "second.png", "#2288bb")
    desktop = _write_desktop(tmp_path / "Changing.desktop", str(first_path))
    provider = QtWidgets.QFileIconProvider()
    clear_linux_icon_cache()

    first = desktop_icon_for_path(desktop, provider)
    # Ensure a distinct metadata timestamp even on coarse filesystems.
    time.sleep(0.002)
    _write_desktop(desktop, str(second_path))
    os.utime(desktop, None)
    second = desktop_icon_for_path(desktop, provider)

    assert first.pixmap(64, 64).toImage().pixelColor(32, 32).name() == "#bb4422"
    assert second.pixmap(64, 64).toImage().pixelColor(32, 32).name() == "#2288bb"


def test_desktop_icon_resolves_freedesktop_theme_name(tmp_path: Path) -> None:
    _app()
    theme_root = tmp_path / "icons"
    theme_dir = theme_root / "ToolboxTest"
    icon_dir = theme_dir / "64x64" / "apps"
    icon_dir.mkdir(parents=True)
    (theme_dir / "index.theme").write_text(
        (
            "[Icon Theme]\n"
            "Name=ToolboxTest\n"
            "Directories=64x64/apps\n\n"
            "[64x64/apps]\n"
            "Size=64\n"
            "Context=Applications\n"
            "Type=Fixed\n"
        ),
        encoding="utf-8",
    )
    _write_png(icon_dir / "toolbox-fixture.png", "#4466cc")
    desktop = _write_desktop(
        tmp_path / "Themed.desktop",
        "toolbox-fixture",
    )
    provider = QtWidgets.QFileIconProvider()
    old_paths = QtGui.QIcon.themeSearchPaths()
    old_theme = QtGui.QIcon.themeName()
    try:
        QtGui.QIcon.setThemeSearchPaths([str(theme_root)])
        QtGui.QIcon.setThemeName("ToolboxTest")
        clear_linux_icon_cache()

        icon = desktop_icon_for_path(desktop, provider)

        assert not icon.isNull()
        image = icon.pixmap(64, 64).toImage()
        assert image.pixelColor(32, 32).name() == "#4466cc"
    finally:
        QtGui.QIcon.setThemeSearchPaths(old_paths)
        QtGui.QIcon.setThemeName(old_theme)
        clear_linux_icon_cache()


def test_initialize_linux_theme_adds_paths_and_fallback(
    tmp_path: Path,
) -> None:
    _app()
    old_paths = QtGui.QIcon.themeSearchPaths()
    old_fallback_paths = QtGui.QIcon.fallbackSearchPaths()
    old_theme = QtGui.QIcon.themeName()
    old_fallback_theme = QtGui.QIcon.fallbackThemeName()
    try:
        QtGui.QIcon.setThemeName("")
        with (
            patch(
                "app.services.linux_icon_theme.linux_icon_theme_search_paths",
                return_value=(str(tmp_path / "icons"),),
            ),
            patch(
                "app.services.linux_icon_theme.linux_icon_fallback_paths",
                return_value=(str(tmp_path / "pixmaps"),),
            ),
            patch(
                "app.services.linux_icon_theme.detect_linux_icon_theme",
                return_value="FixtureTheme",
            ),
        ):
            selected = initialize_linux_icon_theme()

        assert selected == "FixtureTheme"
        assert str(tmp_path / "icons") in QtGui.QIcon.themeSearchPaths()
        assert str(tmp_path / "pixmaps") in QtGui.QIcon.fallbackSearchPaths()
        assert QtGui.QIcon.fallbackThemeName() == "hicolor"
    finally:
        QtGui.QIcon.setThemeSearchPaths(old_paths)
        QtGui.QIcon.setFallbackSearchPaths(old_fallback_paths)
        QtGui.QIcon.setThemeName(old_theme)
        QtGui.QIcon.setFallbackThemeName(old_fallback_theme)
        clear_linux_icon_cache()
