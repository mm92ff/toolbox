#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Persistent image thumbnail helpers for toolbox image previews."""

from __future__ import annotations

import hashlib
from pathlib import Path

from PySide6 import QtCore, QtGui

from app import constants

_CACHE_VARIANT_NORMAL = "normal"
_CACHE_VARIANT_HQ = "hq"


def is_supported_image_path(path: str) -> bool:
    suffix = Path(path).suffix.lower()
    return suffix in constants.IMAGE_PREVIEW_EXTENSIONS


def load_or_create_thumbnail(
    source_path: str,
    icon_size: int,
    mode: str,
    cache_dir: Path | None,
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

    reader = QtGui.QImageReader(str(source))
    reader.setAutoTransform(True)
    image = reader.read()
    if image.isNull():
        return None

    source_pixmap = QtGui.QPixmap.fromImage(image)
    pixmap = _render_thumbnail(source_pixmap, normal_size, normalized_mode)
    if pixmap.isNull():
        return None

    if cache_path is not None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        pixmap.save(str(cache_path), "PNG")
        hq_cache_path = _cache_path_for(
            source,
            hq_size,
            normalized_mode,
            cache_dir,
            variant=_CACHE_VARIANT_HQ,
        )
        if hq_cache_path is not None and not hq_cache_path.exists():
            hq_pixmap = _render_thumbnail(source_pixmap, hq_size, normalized_mode)
            if not hq_pixmap.isNull():
                hq_pixmap.save(str(hq_cache_path), "PNG")

    return pixmap


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
        f"{source.resolve()}|{stat.st_mtime_ns}|{stat.st_size}|{icon_size}|{mode}|{variant}".encode(
            "utf-8"
        )
    )
    digest = hashlib.sha256(key_source).hexdigest()
    return cache_dir / f"{digest}.png"


def _hq_size_for(icon_size: int) -> int:
    # Pre-generate a larger cache variant for fast hover previews.
    return min(512, max(256, int(icon_size) * 2))


def _render_thumbnail(source: QtGui.QPixmap, icon_size: int, mode: str) -> QtGui.QPixmap:
    size = max(1, int(icon_size))
    if mode == constants.IMAGE_PREVIEW_MODE_FILL:
        return _render_fill_thumbnail(source, size)
    return _render_fit_thumbnail(source, size)


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
