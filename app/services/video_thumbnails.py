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

_CACHE_VARIANT_NORMAL = "normal"
_CACHE_VARIANT_HQ = "hq"

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
    source = Path(source_path)
    if not source.exists() or not source.is_file():
        return None

    normalized_mode = _normalize_mode(mode)
    normal_size = max(1, int(icon_size))
    hq_size = _hq_size_for(normal_size)
    cache_path = _cache_path_for(
        source,
        normal_size,
        normalized_mode,
        cache_dir,
        variant=_CACHE_VARIANT_NORMAL,
    )
    if cache_path is not None and cache_path.exists():
        cached = QtGui.QPixmap(str(cache_path))
        if not cached.isNull():
            return cached

    ffmpeg_path = _find_ffmpeg_path(manual_ffmpeg_path)
    if not ffmpeg_path:
        return None

    frame = _extract_video_frame(source, ffmpeg_path, float(capture_seconds))
    if frame is None or frame.isNull():
        return None

    thumb = _render_thumbnail(frame, normal_size, normalized_mode)
    if thumb.isNull():
        return None

    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        thumb.save(str(cache_path), "PNG")
        hq_cache_path = _cache_path_for(
            source,
            hq_size,
            normalized_mode,
            cache_dir,
            variant=_CACHE_VARIANT_HQ,
        )
        if hq_cache_path is not None and not hq_cache_path.exists():
            hq_thumb = _render_thumbnail(frame, hq_size, normalized_mode)
            if not hq_thumb.isNull():
                hq_thumb.save(str(hq_cache_path), "PNG")
    return thumb


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
    except OSError:
        return None

    key_source = (
        f"{source.resolve()}|{stat.st_mtime_ns}|{stat.st_size}|{icon_size}|{mode}|video|{variant}".encode(
            "utf-8"
        )
    )
    digest = hashlib.sha256(key_source).hexdigest()
    return cache_dir / f"{digest}.png"


def _extract_video_frame(source: Path, ffmpeg_path: str, capture_seconds: float) -> QtGui.QPixmap | None:
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
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if result.returncode != 0 or not frame_path.exists():
            return None
        pixmap = QtGui.QPixmap(str(frame_path))
        if pixmap.isNull():
            return None
        return pixmap


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

    system_path = shutil.which("ffmpeg")
    system_candidate = _candidate_file(system_path)
    if system_candidate is not None:
        return FfmpegResolution(system_candidate, FFMPEG_SOURCE_SYSTEM)

    for candidate in _common_windows_ffmpeg_candidates():
        common_candidate = _candidate_file(candidate)
        if common_candidate is not None:
            return FfmpegResolution(common_candidate, FFMPEG_SOURCE_SYSTEM)

    for candidate in _bundled_ffmpeg_candidates():
        if candidate.is_file():
            return FfmpegResolution(str(candidate), FFMPEG_SOURCE_INTERNAL)

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
