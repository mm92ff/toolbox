#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Persistent video thumbnail helpers using ffmpeg when available."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PySide6 import QtCore, QtGui

from app import constants
from app.services.system_utils import external_process_environment
from app.services.thumbnail_cache import (
    load_cached_image,
    pixmap_for_requested_size,
    render_square_thumbnail,
    save_image_atomic,
    thumbnail_bucket_size,
)

_CACHE_VARIANT_NORMAL = "normal"
_CACHE_VARIANT_HQ = "hq"
_CACHE_VARIANT_MASTER = "video-frame-master-v2"

FFMPEG_SOURCE_ENV = "env"
FFMPEG_SOURCE_MANUAL = "manual"
FFMPEG_SOURCE_SYSTEM = "system"
FFMPEG_SOURCE_INTERNAL = "internal"
FFMPEG_SOURCE_NOT_FOUND = "none"


@dataclass(frozen=True)
class FfmpegResolution:
    path: str | None
    source: str = FFMPEG_SOURCE_NOT_FOUND


def is_supported_video_path(path: str) -> bool:
    suffix = Path(path).suffix.lower()
    return suffix in constants.VIDEO_PREVIEW_EXTENSIONS


def load_or_create_video_thumbnail(
    source_path: str,
    icon_size: int,
    mode: str,
    cache_dir: Path | None,
    capture_seconds: float = constants.VIDEO_PREVIEW_CAPTURE_SECONDS,
    manual_ffmpeg_path: str | None = None,
) -> QtGui.QPixmap | None:
    cache_path = prepare_video_thumbnail_cache(
        source_path,
        icon_size,
        mode,
        cache_dir,
        capture_seconds=capture_seconds,
        manual_ffmpeg_path=manual_ffmpeg_path,
    )
    if cache_path is None:
        return None
    pixmap = pixmap_for_requested_size(cache_path, icon_size)
    return None if pixmap.isNull() else pixmap


def cached_video_thumbnail_path(
    source_path: str,
    icon_size: int,
    mode: str,
    cache_dir: Path | None,
) -> Path | None:
    source = Path(source_path)
    if not source.is_file():
        return None
    path = _cache_path_for(source, icon_size, _normalize_mode(mode), cache_dir)
    return path if path is not None and path.is_file() else None


def prepare_video_thumbnail_cache(
    source_path: str,
    icon_size: int,
    mode: str,
    cache_dir: Path | None,
    capture_seconds: float = constants.VIDEO_PREVIEW_CAPTURE_SECONDS,
    manual_ffmpeg_path: str | None = None,
) -> Path | None:
    """Create a reusable video frame and size bucket using worker-safe QImage."""

    source = Path(source_path)
    if not source.is_file() or cache_dir is None:
        return None
    normalized_mode = _normalize_mode(mode)
    cache_path = _cache_path_for(source, icon_size, normalized_mode, cache_dir)
    if cache_path is None:
        return None
    cached = load_cached_image(cache_path)
    if not cached.isNull():
        return cache_path

    master_path = _master_cache_path_for(source, cache_dir, capture_seconds)
    frame = load_cached_image(master_path)
    if frame.isNull():
        ffmpeg_path = _find_ffmpeg_path(manual_ffmpeg_path)
        if not ffmpeg_path:
            return None
        extracted = _extract_video_frame(source, ffmpeg_path, float(capture_seconds))
        frame = _as_qimage(extracted)
        if frame.isNull() or master_path is None or not save_image_atomic(frame, master_path):
            return None

    thumbnail = render_square_thumbnail(
        frame,
        thumbnail_bucket_size(icon_size),
        fill=normalized_mode == constants.IMAGE_PREVIEW_MODE_FILL,
    )
    return cache_path if save_image_atomic(thumbnail, cache_path) else None


def _normalize_mode(mode: str) -> str:
    value = (mode or "").strip().lower()
    if value == constants.IMAGE_PREVIEW_MODE_FILL:
        return constants.IMAGE_PREVIEW_MODE_FILL
    return constants.IMAGE_PREVIEW_MODE_FIT


def _cache_path_for(
    source: Path,
    icon_size: int,
    mode: str,
    cache_dir: Path | None,
    variant: str = _CACHE_VARIANT_NORMAL,
) -> Path | None:
    if cache_dir is None:
        return None
    try:
        stat = source.stat()
        resolved = source.resolve()
    except OSError:
        return None
    bucket = thumbnail_bucket_size(icon_size)
    key_source = f"{resolved}|{stat.st_mtime_ns}|{stat.st_size}|{bucket}|{mode}|video-v2|{variant}".encode("utf-8")
    digest = hashlib.sha256(key_source).hexdigest()
    return cache_dir / f"{digest}.png"


def _master_cache_path_for(
    source: Path,
    cache_dir: Path | None,
    capture_seconds: float,
) -> Path | None:
    if cache_dir is None:
        return None
    try:
        stat = source.stat()
        resolved = source.resolve()
    except OSError:
        return None
    key_source = (
        f"{resolved}|{stat.st_mtime_ns}|{stat.st_size}|{max(0.0, float(capture_seconds)):.3f}|"
        f"{_CACHE_VARIANT_MASTER}"
    ).encode("utf-8")
    return cache_dir / f"{hashlib.sha256(key_source).hexdigest()}.png"


def _extract_video_frame(source: Path, ffmpeg_path: str, capture_seconds: float) -> QtGui.QImage | None:
    with tempfile.TemporaryDirectory() as tmp:
        frame_path = Path(tmp) / "frame.png"
        cmd = [
            ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{max(0.0, capture_seconds):.3f}",
            "-i",
            str(source),
            "-frames:v",
            "1",
            str(frame_path),
        ]
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=12,
                check=False,
                env=external_process_environment(ffmpeg_path),
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if result.returncode != 0 or not frame_path.exists():
            return None
        image = QtGui.QImage(str(frame_path))
        if image.isNull():
            return None
        return image


def _as_qimage(value: QtGui.QImage | QtGui.QPixmap | None) -> QtGui.QImage:
    if isinstance(value, QtGui.QImage):
        return value
    if isinstance(value, QtGui.QPixmap):
        return value.toImage()
    return QtGui.QImage()


def clear_ffmpeg_resolution_cache() -> None:
    _resolve_ffmpeg_path_cached.cache_clear()


def resolve_ffmpeg_path(manual_ffmpeg_path: str | None = None) -> FfmpegResolution:
    normalized_manual = _normalize_candidate_path(manual_ffmpeg_path)
    normalized_env_override = _normalize_candidate_path(os.environ.get("TOOLBOX_FFMPEG_PATH"))
    return _resolve_ffmpeg_path_cached(normalized_manual, normalized_env_override)


@lru_cache(maxsize=32)
def _resolve_ffmpeg_path_cached(
    normalized_manual_path: str,
    normalized_env_override: str,
) -> FfmpegResolution:
    env_candidate = _candidate_file(normalized_env_override)
    if env_candidate is not None:
        return FfmpegResolution(env_candidate, FFMPEG_SOURCE_ENV)

    manual_candidate = _candidate_file(normalized_manual_path)
    if manual_candidate is not None:
        return FfmpegResolution(manual_candidate, FFMPEG_SOURCE_MANUAL)

    for candidate in _bundled_ffmpeg_candidates():
        if candidate.is_file():
            return FfmpegResolution(str(candidate), FFMPEG_SOURCE_INTERNAL)

    system_path = shutil.which("ffmpeg")
    system_candidate = _candidate_file(system_path)
    if system_candidate is not None:
        return FfmpegResolution(system_candidate, FFMPEG_SOURCE_SYSTEM)

    for candidate in _common_windows_ffmpeg_candidates():
        common_candidate = _candidate_file(candidate)
        if common_candidate is not None:
            return FfmpegResolution(common_candidate, FFMPEG_SOURCE_SYSTEM)

    return FfmpegResolution(None, FFMPEG_SOURCE_NOT_FOUND)


def _normalize_candidate_path(value: str | None) -> str:
    text = (value or "").strip().strip('"')
    if not text:
        return ""
    try:
        return str(Path(text).expanduser().resolve(strict=False))
    except OSError:
        return str(Path(text).expanduser())


def _candidate_file(value: str | os.PathLike[str] | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        candidate = Path(text).expanduser().resolve(strict=False)
    except OSError:
        return None
    if candidate.is_file():
        return str(candidate)
    return None


def _find_ffmpeg_path(manual_ffmpeg_path: str | None = None) -> str | None:
    return resolve_ffmpeg_path(manual_ffmpeg_path).path


def _common_windows_ffmpeg_candidates() -> list[Path]:
    if os.name != "nt":
        return []
    candidates: list[Path] = []
    binary_name = "ffmpeg.exe"

    program_files = os.environ.get("ProgramFiles", "").strip()
    if program_files:
        base = Path(program_files)
        candidates.append(base / "ffmpeg" / "bin" / binary_name)
        candidates.append(base / "FFmpeg" / "bin" / binary_name)

    program_files_x86 = os.environ.get("ProgramFiles(x86)", "").strip()
    if program_files_x86:
        base = Path(program_files_x86)
        candidates.append(base / "ffmpeg" / "bin" / binary_name)
        candidates.append(base / "FFmpeg" / "bin" / binary_name)

    chocolatey_base = os.environ.get("ChocolateyInstall", r"C:\ProgramData\chocolatey").strip()
    if chocolatey_base:
        base = Path(chocolatey_base)
        candidates.append(base / "bin" / binary_name)
        candidates.append(base / "lib" / "ffmpeg" / "tools" / "ffmpeg" / "bin" / binary_name)

    user_profile = os.environ.get("USERPROFILE", "").strip()
    if user_profile:
        candidates.append(Path(user_profile) / "scoop" / "apps" / "ffmpeg" / "current" / "bin" / binary_name)

    local_app_data = os.environ.get("LOCALAPPDATA", "").strip()
    if local_app_data:
        winget_root = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        winget_patterns = (
            "*FFmpeg*_*",
            "*ffmpeg*_*",
        )
        for pattern in winget_patterns:
            for package_dir in winget_root.glob(pattern):
                if not package_dir.is_dir():
                    continue
                try:
                    package_children = list(package_dir.iterdir())
                except OSError:
                    continue
                for inner in package_children:
                    if inner.is_dir():
                        candidates.append(inner / "bin" / binary_name)

    deduped: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(path)
    return deduped


def _bundled_ffmpeg_candidates() -> list[Path]:
    binary_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    candidates: list[Path] = []

    xdg_data_home = os.environ.get("XDG_DATA_HOME", "").strip()
    user_data_root = (
        Path(xdg_data_home).expanduser()
        if xdg_data_home
        else Path.home() / ".local" / "share"
    )
    candidates.append(user_data_root / "toolbox" / "ffmpeg" / "7.0.2" / binary_name)

    appdir = os.environ.get("APPDIR")
    if appdir:
        bundle_root = Path(appdir)
        candidates.append(bundle_root / "usr" / "bin" / binary_name)
        candidates.append(bundle_root / binary_name)
        candidates.append(bundle_root / "bin" / binary_name)

    project_root = Path(__file__).resolve().parent.parent.parent
    candidates.append(project_root / ".bin" / binary_name)

    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        bundle_root = Path(meipass)
        candidates.append(bundle_root / binary_name)
        candidates.append(bundle_root / "bin" / binary_name)

    exe_dir = Path(sys.executable).resolve().parent
    candidates.append(exe_dir / binary_name)
    candidates.append(exe_dir / "bin" / binary_name)
    return candidates


def _render_thumbnail(source: QtGui.QPixmap, size: int, mode: str) -> QtGui.QPixmap:
    if mode == constants.IMAGE_PREVIEW_MODE_FILL:
        return _render_fill_thumbnail(source, size)
    return _render_fit_thumbnail(source, size)


def _hq_size_for(icon_size: int) -> int:
    # Pre-generate a larger cache variant for fast hover previews.
    return min(512, max(256, int(icon_size) * 2))


def _render_fit_thumbnail(source: QtGui.QPixmap, size: int) -> QtGui.QPixmap:
    target = QtGui.QPixmap(size, size)
    target.fill(QtCore.Qt.GlobalColor.transparent)
    scaled = source.scaled(
        size,
        size,
        QtCore.Qt.AspectRatioMode.KeepAspectRatio,
        QtCore.Qt.TransformationMode.SmoothTransformation,
    )
    x = (size - scaled.width()) // 2
    y = (size - scaled.height()) // 2
    painter = QtGui.QPainter(target)
    try:
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawPixmap(x, y, scaled)
    finally:
        painter.end()
    return target


def _render_fill_thumbnail(source: QtGui.QPixmap, size: int) -> QtGui.QPixmap:
    sw = max(1, source.width())
    sh = max(1, source.height())
    scale = max(size / sw, size / sh)
    scaled_w = max(size, int(round(sw * scale)))
    scaled_h = max(size, int(round(sh * scale)))
    scaled = source.scaled(
        scaled_w,
        scaled_h,
        QtCore.Qt.AspectRatioMode.IgnoreAspectRatio,
        QtCore.Qt.TransformationMode.SmoothTransformation,
    )
    crop_x = max(0, (scaled.width() - size) // 2)
    crop_y = max(0, (scaled.height() - size) // 2)
    return scaled.copy(crop_x, crop_y, size, size)
