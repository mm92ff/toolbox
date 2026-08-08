#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Persistent, size-bucketed image thumbnails safe for background workers."""

from __future__ import annotations

import hashlib
from pathlib import Path

from PySide6 import QtCore, QtGui

from app import constants
from app.services.thumbnail_cache import (
    MASTER_THUMBNAIL_SIZE,
    load_cached_image,
    pixmap_for_requested_size,
    render_square_thumbnail,
    save_image_atomic,
    thumbnail_bucket_size,
)

_CACHE_VARIANT_NORMAL = "normal"
_CACHE_VARIANT_HQ = "hq"  # Kept for compatibility with older private callers.
_CACHE_VARIANT_MASTER = "image-master-v2"


def is_supported_image_path(path: str) -> bool:
    return Path(path).suffix.lower() in constants.IMAGE_PREVIEW_EXTENSIONS


def cached_thumbnail_path(
    source_path: str,
    icon_size: int,
    mode: str,
    cache_dir: Path | None,
) -> Path | None:
    """Return an existing reusable cache bucket without decoding the source."""

    source = Path(source_path)
    if not source.is_file():
        return None
    path = _cache_path_for(source, icon_size, _normalize_mode(mode), cache_dir)
    return path if path is not None and path.is_file() else None


def prepare_thumbnail_cache(
    source_path: str,
    icon_size: int,
    mode: str,
    cache_dir: Path | None,
) -> Path | None:
    """Create a master and requested size bucket using QImage-only operations."""

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

    master_path = _master_cache_path_for(source, cache_dir)
    master = load_cached_image(master_path)
    if master.isNull():
        master = _read_scaled_master(source)
        if master.isNull() or master_path is None or not save_image_atomic(master, master_path):
            return None

    bucket = thumbnail_bucket_size(icon_size)
    thumbnail = render_square_thumbnail(
        master,
        bucket,
        fill=normalized_mode == constants.IMAGE_PREVIEW_MODE_FILL,
    )
    return cache_path if save_image_atomic(thumbnail, cache_path) else None


def load_or_create_thumbnail(
    source_path: str,
    icon_size: int,
    mode: str,
    cache_dir: Path | None,
) -> QtGui.QPixmap | None:
    """Synchronous compatibility API used by hover previews and tests."""

    cache_path = prepare_thumbnail_cache(source_path, icon_size, mode, cache_dir)
    if cache_path is None:
        return None
    pixmap = pixmap_for_requested_size(cache_path, icon_size)
    return None if pixmap.isNull() else pixmap


def _read_scaled_master(source: Path) -> QtGui.QImage:
    reader = QtGui.QImageReader(str(source))
    reader.setAutoTransform(True)
    source_size = reader.size()
    if source_size.isValid() and (
        source_size.width() > MASTER_THUMBNAIL_SIZE
        or source_size.height() > MASTER_THUMBNAIL_SIZE
    ):
        source_size.scale(
            MASTER_THUMBNAIL_SIZE,
            MASTER_THUMBNAIL_SIZE,
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
        )
        reader.setScaledSize(source_size)
    return reader.read()


def _normalize_mode(mode: str) -> str:
    return (
        constants.IMAGE_PREVIEW_MODE_FILL
        if (mode or "").strip().lower() == constants.IMAGE_PREVIEW_MODE_FILL
        else constants.IMAGE_PREVIEW_MODE_FIT
    )


def _source_digest(source: Path, variant: str) -> str | None:
    try:
        stat = source.stat()
        resolved = source.resolve()
    except OSError:
        return None
    material = f"{resolved}|{stat.st_mtime_ns}|{stat.st_size}|{variant}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _master_cache_path_for(source: Path, cache_dir: Path | None) -> Path | None:
    if cache_dir is None:
        return None
    digest = _source_digest(source, _CACHE_VARIANT_MASTER)
    return None if digest is None else cache_dir / f"{digest}.png"


def _cache_path_for(
    source: Path,
    icon_size: int,
    mode: str,
    cache_dir: Path | None,
    variant: str = _CACHE_VARIANT_NORMAL,
) -> Path | None:
    if cache_dir is None:
        return None
    bucket = thumbnail_bucket_size(icon_size)
    digest = _source_digest(source, f"image-v2|{bucket}|{mode}|{variant}")
    return None if digest is None else cache_dir / f"{digest}.png"


def _hq_size_for(icon_size: int) -> int:
    return min(512, max(256, int(icon_size) * 2))


def _render_thumbnail(source: QtGui.QPixmap, icon_size: int, mode: str) -> QtGui.QPixmap:
    image = source.toImage()
    rendered = render_square_thumbnail(
        image,
        icon_size,
        fill=_normalize_mode(mode) == constants.IMAGE_PREVIEW_MODE_FILL,
    )
    return QtGui.QPixmap.fromImage(rendered)


def _render_fit_thumbnail(source: QtGui.QPixmap, size: int) -> QtGui.QPixmap:
    return _render_thumbnail(source, size, constants.IMAGE_PREVIEW_MODE_FIT)


def _render_fill_thumbnail(source: QtGui.QPixmap, size: int) -> QtGui.QPixmap:
    return _render_thumbnail(source, size, constants.IMAGE_PREVIEW_MODE_FILL)
