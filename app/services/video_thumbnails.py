#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Persistent video thumbnail helpers using ffmpeg when available."""

from __future__ import annotations

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


def is_supported_video_path(path: str) -> bool:
    suffix = Path(path).suffix.lower()
    return suffix in constants.VIDEO_PREVIEW_EXTENSIONS


def load_or_create_video_thumbnail(
    source_path: str,
    icon_size: int,
    mode: str,
    cache_dir: Path | None,
    capture_seconds: float = constants.VIDEO_PREVIEW_CAPTURE_SECONDS,
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

    ffmpeg_path = _find_ffmpeg_path()
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


def _find_ffmpeg_path() -> str | None:
    env_override = (os.environ.get("TOOLBOX_FFMPEG_PATH") or "").strip()
    if env_override:
        override_path = Path(env_override)
        if override_path.is_file():
            return str(override_path)

    for candidate in _bundled_ffmpeg_candidates():
        if candidate.is_file():
            return str(candidate)

    return shutil.which("ffmpeg")


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
