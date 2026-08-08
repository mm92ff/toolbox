#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared helpers for bounded, reusable media thumbnail caches."""

from __future__ import annotations

import os
import time
from pathlib import Path

from PySide6 import QtCore, QtGui


THUMBNAIL_SIZE_BUCKETS = (64, 96, 128, 192, 256, 384, 512)
MASTER_THUMBNAIL_SIZE = 512


def thumbnail_bucket_size(requested_size: int) -> int:
    """Return the smallest reusable cache size that covers ``requested_size``."""

    size = max(1, int(requested_size))
    for bucket in THUMBNAIL_SIZE_BUCKETS:
        if size <= bucket:
            return bucket
    return THUMBNAIL_SIZE_BUCKETS[-1]


def render_square_thumbnail(
    source: QtGui.QImage,
    size: int,
    *,
    fill: bool,
) -> QtGui.QImage:
    """Render a square fit/fill thumbnail without using GUI-thread-only QPixmap."""

    target_size = max(1, int(size))
    if source.isNull():
        return QtGui.QImage()

    aspect_mode = (
        QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding
        if fill
        else QtCore.Qt.AspectRatioMode.KeepAspectRatio
    )
    scaled = source.scaled(
        target_size,
        target_size,
        aspect_mode,
        QtCore.Qt.TransformationMode.SmoothTransformation,
    )
    if scaled.isNull():
        return QtGui.QImage()

    if fill:
        x = max(0, (scaled.width() - target_size) // 2)
        y = max(0, (scaled.height() - target_size) // 2)
        return scaled.copy(x, y, target_size, target_size)

    result = QtGui.QImage(
        target_size,
        target_size,
        QtGui.QImage.Format.Format_ARGB32_Premultiplied,
    )
    result.fill(QtCore.Qt.GlobalColor.transparent)
    painter = QtGui.QPainter(result)
    try:
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.drawImage(
            (target_size - scaled.width()) // 2,
            (target_size - scaled.height()) // 2,
            scaled,
        )
    finally:
        painter.end()
    return result


def save_image_atomic(image: QtGui.QImage, path: Path) -> bool:
    """Write a PNG atomically so parallel readers never see a partial file."""

    if image.isNull():
        return False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False
    output = QtCore.QSaveFile(str(path))
    if not output.open(QtCore.QIODevice.OpenModeFlag.WriteOnly):
        return False
    if not image.save(output, "PNG"):
        output.cancelWriting()
        return False
    return bool(output.commit())


def load_cached_image(path: Path | None, *, touch: bool = False) -> QtGui.QImage:
    if path is None or not path.is_file():
        return QtGui.QImage()
    image = QtGui.QImage(str(path))
    if image.isNull():
        return image
    if touch:
        try:
            os.utime(path, None)
        except OSError:
            pass
    return image


def pixmap_for_requested_size(path: Path | str, requested_size: int) -> QtGui.QPixmap:
    """Load a cached square and scale it to the exact current widget size."""

    pixmap = QtGui.QPixmap(str(path))
    size = max(1, int(requested_size))
    if pixmap.isNull() or pixmap.size() == QtCore.QSize(size, size):
        return pixmap
    return pixmap.scaled(
        size,
        size,
        QtCore.Qt.AspectRatioMode.IgnoreAspectRatio,
        QtCore.Qt.TransformationMode.SmoothTransformation,
    )


def prune_thumbnail_cache(cache_dir: Path, max_bytes: int) -> tuple[int, int]:
    """Remove least-recently-used PNG files until the cache fits the quota."""

    limit = max(0, int(max_bytes))
    try:
        files = [path for path in cache_dir.glob("*.png") if path.is_file()]
    except OSError:
        return (0, 0)

    records: list[tuple[float, int, Path]] = []
    total = 0
    for path in files:
        try:
            stat = path.stat()
        except OSError:
            continue
        total += stat.st_size
        records.append((stat.st_mtime, stat.st_size, path))

    removed = 0
    if total <= limit:
        return (removed, total)
    records.sort(key=lambda record: record[0])
    # Leave a little headroom so pruning is not retriggered after every write.
    target = int(limit * 0.9)
    for _mtime, size, path in records:
        if total <= target:
            break
        try:
            path.unlink()
        except OSError:
            continue
        total -= size
        removed += 1
    return (removed, max(0, total))


def cache_prune_due(last_prune: float, interval_seconds: float) -> bool:
    return time.monotonic() - float(last_prune) >= max(0.0, interval_seconds)
