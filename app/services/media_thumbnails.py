#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bounded asynchronous image/video thumbnail generation."""

from __future__ import annotations

import os
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path

from PySide6 import QtCore

from app import constants
from app.services.image_thumbnails import cached_thumbnail_path, prepare_thumbnail_cache
from app.services.thumbnail_cache import (
    cache_prune_due,
    prune_thumbnail_cache,
    thumbnail_bucket_size,
)
from app.services.video_thumbnails import (
    cached_video_thumbnail_path,
    prepare_video_thumbnail_cache,
)

MEDIA_KIND_IMAGE = "image"
MEDIA_KIND_VIDEO = "video"


@dataclass(frozen=True)
class MediaThumbnailRequest:
    path: str
    kind: str
    signature: tuple[int, int]
    bucket_size: int
    mode: str
    cache_dir: Path
    capture_seconds: float
    manual_ffmpeg_path: str

    @property
    def source_key(self) -> tuple[str, str]:
        return (self.kind, self.path)

    @property
    def request_key(self) -> tuple[object, ...]:
        return (
            self.kind,
            self.path,
            self.signature,
            self.bucket_size,
            self.mode,
            str(self.cache_dir),
            round(self.capture_seconds, 3),
        )


class _MediaThumbnailSignals(QtCore.QObject):
    completed = QtCore.Signal(object, str, str)


class _MediaThumbnailTask(QtCore.QRunnable):
    def __init__(self, request: MediaThumbnailRequest) -> None:
        super().__init__()
        self.request = request
        self.signals = _MediaThumbnailSignals()

    def run(self) -> None:
        output: Path | None = None
        error = ""
        try:
            if self.request.kind == MEDIA_KIND_IMAGE:
                output = prepare_thumbnail_cache(
                    self.request.path,
                    self.request.bucket_size,
                    self.request.mode,
                    self.request.cache_dir,
                )
            else:
                output = prepare_video_thumbnail_cache(
                    self.request.path,
                    self.request.bucket_size,
                    self.request.mode,
                    self.request.cache_dir,
                    capture_seconds=self.request.capture_seconds,
                    manual_ffmpeg_path=self.request.manual_ffmpeg_path,
                )
        except Exception as exc:  # Never let a corrupt media file kill a worker.
            error = str(exc)
        self.signals.completed.emit(self.request, str(output or ""), error)


class _CachePruneSignals(QtCore.QObject):
    completed = QtCore.Signal(str)


class _CachePruneTask(QtCore.QRunnable):
    def __init__(self, cache_dir: Path, max_bytes: int) -> None:
        super().__init__()
        self.cache_dir = cache_dir
        self.max_bytes = max_bytes
        self.signals = _CachePruneSignals()

    def run(self) -> None:
        prune_thumbnail_cache(self.cache_dir, self.max_bytes)
        self.signals.completed.emit(str(self.cache_dir))


class MediaThumbnailService(QtCore.QObject):
    """Deduplicate media work and keep video extraction off the GUI thread."""

    result_ready = QtCore.Signal(str, str, int, str, str)

    def __init__(
        self,
        parent: QtCore.QObject | None = None,
        *,
        image_workers: int = 3,
        video_workers: int = 2,
    ) -> None:
        super().__init__(parent)
        self._image_pool = QtCore.QThreadPool(self)
        self._image_pool.setMaxThreadCount(max(1, int(image_workers)))
        self._video_pool = QtCore.QThreadPool(self)
        self._video_pool.setMaxThreadCount(max(1, int(video_workers)))
        self._maintenance_pool = QtCore.QThreadPool(self)
        self._maintenance_pool.setMaxThreadCount(1)
        self._active: dict[tuple[str, str], _MediaThumbnailTask] = {}
        self._queued: dict[
            tuple[str, str], OrderedDict[tuple[object, ...], MediaThumbnailRequest]
        ] = {}
        self._prune_tasks: dict[str, _CachePruneTask] = {}
        self._last_prune: dict[str, float] = {}
        self._accept_results = True

    @property
    def image_workers(self) -> int:
        return self._image_pool.maxThreadCount()

    @property
    def video_workers(self) -> int:
        return self._video_pool.maxThreadCount()

    def request(
        self,
        path: str,
        kind: str,
        icon_size: int,
        mode: str,
        cache_dir: Path | None,
        *,
        capture_seconds: float = constants.VIDEO_PREVIEW_CAPTURE_SECONDS,
        manual_ffmpeg_path: str = "",
        priority: int = 0,
    ) -> None:
        if not self._accept_results or cache_dir is None:
            return
        normalized = os.path.abspath(os.path.expanduser(path))
        signature = self._file_signature(normalized)
        if signature is None or kind not in {MEDIA_KIND_IMAGE, MEDIA_KIND_VIDEO}:
            return
        normalized_mode = (mode or "").strip().lower()
        bucket = thumbnail_bucket_size(icon_size)
        cache_path = self.cached_path(normalized, kind, bucket, normalized_mode, cache_dir)
        if cache_path is not None:
            try:
                os.utime(cache_path, None)
            except OSError:
                pass
            QtCore.QTimer.singleShot(
                0,
                lambda p=normalized, k=kind, b=bucket, m=normalized_mode, c=str(cache_path):
                    self.result_ready.emit(p, k, b, m, c),
            )
            self._maybe_prune(cache_dir)
            return

        request = MediaThumbnailRequest(
            path=normalized,
            kind=kind,
            signature=signature,
            bucket_size=bucket,
            mode=normalized_mode,
            cache_dir=Path(cache_dir),
            capture_seconds=float(capture_seconds),
            manual_ffmpeg_path=(manual_ffmpeg_path or "").strip(),
        )
        source_key = request.source_key
        active = self._active.get(source_key)
        if active is not None:
            if active.request.request_key != request.request_key:
                self._queued.setdefault(source_key, OrderedDict())[request.request_key] = request
            return
        self._start(request, priority)
        self._maybe_prune(cache_dir)

    @staticmethod
    def cached_path(
        path: str,
        kind: str,
        icon_size: int,
        mode: str,
        cache_dir: Path | None,
    ) -> Path | None:
        if kind == MEDIA_KIND_IMAGE:
            return cached_thumbnail_path(path, icon_size, mode, cache_dir)
        if kind == MEDIA_KIND_VIDEO:
            return cached_video_thumbnail_path(path, icon_size, mode, cache_dir)
        return None

    def _start(self, request: MediaThumbnailRequest, priority: int = 0) -> None:
        if not self._accept_results:
            return
        task = _MediaThumbnailTask(request)
        task.signals.completed.connect(self._on_completed)
        self._active[request.source_key] = task
        pool = self._image_pool if request.kind == MEDIA_KIND_IMAGE else self._video_pool
        pool.start(task, int(priority))

    @QtCore.Slot(object, str, str)
    def _on_completed(
        self,
        request_object: object,
        thumbnail_path: str,
        _error: str,
    ) -> None:
        if not isinstance(request_object, MediaThumbnailRequest):
            return
        request = request_object
        self._active.pop(request.source_key, None)
        if (
            self._accept_results
            and thumbnail_path
            and self._file_signature(request.path) == request.signature
        ):
            self.result_ready.emit(
                request.path,
                request.kind,
                request.bucket_size,
                request.mode,
                thumbnail_path,
            )

        queued = self._queued.get(request.source_key)
        while self._accept_results and queued:
            _key, next_request = queued.popitem(last=False)
            if self._file_signature(next_request.path) != next_request.signature:
                continue
            self._start(next_request)
            break
        if queued is not None and not queued:
            self._queued.pop(request.source_key, None)
        if not self._active:
            self._maybe_prune(request.cache_dir)

    @staticmethod
    def _file_signature(path: str) -> tuple[int, int] | None:
        try:
            stat = os.stat(path, follow_symlinks=False)
        except OSError:
            return None
        return (stat.st_mtime_ns, stat.st_size)

    def _maybe_prune(self, cache_dir: Path) -> None:
        # Never remove a master or bucket while a worker may be reading it.
        if self._active:
            return
        key = str(Path(cache_dir))
        last = self._last_prune.get(key, 0.0)
        if key in self._prune_tasks or not cache_prune_due(
            last, constants.THUMBNAIL_CACHE_PRUNE_INTERVAL_SECONDS
        ):
            return
        self._last_prune[key] = time.monotonic()
        task = _CachePruneTask(Path(cache_dir), constants.THUMBNAIL_CACHE_MAX_BYTES)
        task.signals.completed.connect(self._on_prune_completed)
        self._prune_tasks[key] = task
        self._maintenance_pool.start(task)

    @QtCore.Slot(str)
    def _on_prune_completed(self, cache_dir: str) -> None:
        self._prune_tasks.pop(cache_dir, None)

    def shutdown(self) -> None:
        self._accept_results = False
        self._image_pool.clear()
        self._video_pool.clear()
        self._maintenance_pool.clear()
        self._active.clear()
        self._queued.clear()
        self._prune_tasks.clear()
