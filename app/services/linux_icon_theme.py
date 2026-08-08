#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Freedesktop icon-theme setup and desktop-entry icon resolution."""

from __future__ import annotations

from functools import lru_cache
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Mapping

from PySide6 import QtCore, QtGui, QtWidgets

from app.services.appimage_icons import (
    AppImageIconService,
    cached_appimage_icon_path,
    is_appimage_path,
)
from app.services.desktop_entries import DesktopEntryError, read_desktop_entry


logger = logging.getLogger(__name__)


def linux_icon_theme_search_paths(
    environment: Mapping[str, str] | None = None,
    *,
    home: Path | None = None,
) -> tuple[str, ...]:
    """Return ordered freedesktop icon-theme roots."""

    env = environment if environment is not None else os.environ
    user_home = home or Path.home()
    xdg_data_home = (env.get("XDG_DATA_HOME") or "").strip()
    user_data_root = (
        Path(xdg_data_home).expanduser()
        if xdg_data_home
        else user_home / ".local" / "share"
    )
    raw_system_roots = (env.get("XDG_DATA_DIRS") or "").strip()
    system_roots = (
        [Path(item).expanduser() for item in raw_system_roots.split(":") if item]
        if raw_system_roots
        else [Path("/usr/local/share"), Path("/usr/share")]
    )

    candidates = [
        user_data_root / "icons",
        *(root / "icons" for root in system_roots),
        Path("/usr/local/share/icons"),
        Path("/usr/share/icons"),
    ]
    ordered: list[str] = []
    for candidate in candidates:
        normalized = str(candidate)
        if normalized not in ordered:
            ordered.append(normalized)
    return tuple(ordered)


def linux_icon_fallback_paths(
    environment: Mapping[str, str] | None = None,
    *,
    home: Path | None = None,
) -> tuple[str, ...]:
    """Return standalone icon-file fallback paths."""

    env = environment if environment is not None else os.environ
    user_home = home or Path.home()
    xdg_data_home = (env.get("XDG_DATA_HOME") or "").strip()
    user_data_root = (
        Path(xdg_data_home).expanduser()
        if xdg_data_home
        else user_home / ".local" / "share"
    )
    candidates = (
        user_data_root / "pixmaps",
        Path("/usr/local/share/pixmaps"),
        Path("/usr/share/pixmaps"),
    )
    return tuple(dict.fromkeys(str(candidate) for candidate in candidates))


def _read_gsettings_value(schema: str, key: str) -> str:
    gsettings = shutil.which("gsettings")
    if not gsettings:
        return ""
    child_environment = os.environ.copy()
    original_library_path = child_environment.get("LD_LIBRARY_PATH_ORIG")
    if original_library_path:
        child_environment["LD_LIBRARY_PATH"] = original_library_path
    elif "LD_LIBRARY_PATH_ORIG" in child_environment:
        child_environment.pop("LD_LIBRARY_PATH", None)
    try:
        completed = subprocess.run(
            [gsettings, "get", schema, key],
            check=False,
            capture_output=True,
            text=True,
            timeout=1.5,
            env=child_environment,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if completed.returncode != 0:
        return ""
    value = completed.stdout.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return value.strip()


def detect_linux_icon_theme() -> str:
    """Detect the desktop icon theme with Cinnamon-first fallbacks."""

    current = QtGui.QIcon.themeName().strip()
    if current:
        return current
    for schema in (
        "org.cinnamon.desktop.interface",
        "org.gnome.desktop.interface",
    ):
        detected = _read_gsettings_value(schema, "icon-theme")
        if detected:
            return detected
    return "hicolor"


def initialize_linux_icon_theme() -> str:
    """Configure Qt theme lookup for bundled Linux applications."""

    if not sys.platform.startswith("linux"):
        return QtGui.QIcon.themeName()

    search_paths = list(QtGui.QIcon.themeSearchPaths())
    for path in linux_icon_theme_search_paths():
        if path not in search_paths:
            search_paths.append(path)
    if ":/icons" not in search_paths:
        search_paths.append(":/icons")
    QtGui.QIcon.setThemeSearchPaths(search_paths)

    fallback_paths = list(QtGui.QIcon.fallbackSearchPaths())
    for path in linux_icon_fallback_paths():
        if path not in fallback_paths:
            fallback_paths.append(path)
    QtGui.QIcon.setFallbackSearchPaths(fallback_paths)
    QtGui.QIcon.setFallbackThemeName("hicolor")

    theme = detect_linux_icon_theme()
    QtGui.QIcon.setThemeName(theme or "hicolor")
    clear_linux_icon_cache()
    logger.debug(
        "Linux icon theme initialized: theme=%s, search_paths=%s",
        QtGui.QIcon.themeName(),
        len(QtGui.QIcon.themeSearchPaths()),
    )
    return QtGui.QIcon.themeName()


@lru_cache(maxsize=512)
def _declared_desktop_icon(
    path_text: str,
    mtime_ns: int,
    size: int,
    theme_name: str,
) -> QtGui.QIcon:
    del mtime_ns, size, theme_name
    path = Path(path_text)
    try:
        metadata = read_desktop_entry(path)
    except DesktopEntryError:
        return QtGui.QIcon()
    icon_value = metadata.icon.strip()
    if not icon_value:
        return QtGui.QIcon()

    icon_path = Path(icon_value).expanduser()
    if icon_path.is_absolute():
        if icon_path.is_file():
            return QtGui.QIcon(str(icon_path))
        return QtGui.QIcon()
    if "/" in icon_value:
        relative_icon = (path.parent / icon_path).resolve(strict=False)
        if relative_icon.is_file():
            return QtGui.QIcon(str(relative_icon))
        return QtGui.QIcon()

    icon = QtGui.QIcon.fromTheme(icon_value)
    if not icon.isNull():
        return icon
    suffix = Path(icon_value).suffix.lower()
    if suffix in {".png", ".svg", ".svgz", ".xpm"}:
        return QtGui.QIcon.fromTheme(Path(icon_value).stem)
    return QtGui.QIcon()


_SIDECAR_SUFFIXES = (".png", ".svg", ".svgz", ".ico", ".jpg", ".jpeg", ".xpm")


@lru_cache(maxsize=1024)
def _sidecar_icon_path(
    path_text: str,
    target_mtime_ns: int,
    target_size: int,
    parent_mtime_ns: int,
) -> str:
    """Return a passive sidecar image path, caching misses until metadata changes."""

    del target_mtime_ns, target_size, parent_mtime_ns
    path = Path(path_text)
    expected_names = {
        f"{path.name}{suffix}".casefold() for suffix in _SIDECAR_SUFFIXES
    }
    expected_names.update(
        f"{path.stem}{suffix}".casefold() for suffix in _SIDECAR_SUFFIXES
    )
    try:
        candidates = sorted(path.parent.iterdir(), key=lambda item: item.name.casefold())
    except OSError as exc:
        logger.debug("Could not inspect sidecar icons beside '%s': %s", path.name, exc)
        return ""
    for candidate in candidates:
        if candidate.name.casefold() not in expected_names:
            continue
        try:
            if candidate.is_file():
                return str(candidate)
        except OSError as exc:
            logger.debug("Could not inspect sidecar icon '%s': %s", candidate.name, exc)
    return ""


def desktop_icon_for_path(
    filepath: str | Path,
    icon_provider: QtWidgets.QFileIconProvider,
    fallback: QtGui.QIcon | None = None,
    appimage_icon_service: AppImageIconService | None = None,
) -> QtGui.QIcon:
    """Resolve a desktop entry's declared icon with safe fallbacks."""

    path = Path(filepath).expanduser()
    if path.suffix.lower() == ".desktop":
        try:
            stat = path.stat()
            icon = _declared_desktop_icon(
                str(path.resolve(strict=False)),
                stat.st_mtime_ns,
                stat.st_size,
                QtGui.QIcon.themeName(),
            )
            if not icon.isNull():
                return icon
        except OSError as exc:
            logger.debug("Could not inspect desktop icon metadata for '%s': %s", path.name, exc)

    # Sidecar icons are passive data and therefore safe to inspect. Never run the
    # target itself merely to obtain metadata: arbitrary executable files are
    # valid toolbox entries and may have side effects even with unknown options.
    try:
        target_stat = path.stat()
        target_mtime_ns = target_stat.st_mtime_ns
        target_size = target_stat.st_size
    except OSError:
        target_mtime_ns = -1
        target_size = -1
    try:
        parent_mtime_ns = path.parent.stat().st_mtime_ns
    except OSError:
        parent_mtime_ns = -1
    sidecar_path = _sidecar_icon_path(
        str(path.resolve(strict=False)),
        target_mtime_ns,
        target_size,
        parent_mtime_ns,
    )
    if sidecar_path:
        sidecar_icon = QtGui.QIcon(sidecar_path)
        if not sidecar_icon.isNull():
            return sidecar_icon

    if is_appimage_path(path):
        cached_icon_path = cached_appimage_icon_path(path)
        if cached_icon_path:
            cached_icon = QtGui.QIcon(cached_icon_path)
            if not cached_icon.isNull():
                return cached_icon
        if appimage_icon_service is not None:
            appimage_icon_service.request(path)

    icon = icon_provider.icon(QtCore.QFileInfo(str(path)))
    if not icon.isNull():
        return icon
    return fallback if fallback is not None else QtGui.QIcon()


def clear_linux_icon_cache() -> None:
    """Clear resolved desktop icons after file or theme changes."""

    _declared_desktop_icon.cache_clear()
    _sidecar_icon_path.cache_clear()
