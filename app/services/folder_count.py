#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Bounded asynchronous folder counting shared by canvas tiles."""

from __future__ import annotations

import os
import time

from PySide6 import QtCore


class _FolderCountSignals(QtCore.QObject):
    completed = QtCore.Signal(str, int, int, str)


class _FolderCountTask(QtCore.QRunnable):
    def __init__(self, path: str, generation: int) -> None:
        super().__init__()
        self.path = path
        self.generation = generation
        self.signals = _FolderCountSignals()

    def run(self) -> None:
        count = 0
        error = ""
        try:
            with os.scandir(self.path) as entries:
                for entry in entries:
                    if entry.name.startswith("."):
                        continue
                    count += 1
        except PermissionError:
            error = "Keine Leseberechtigung"
        except OSError as exc:
            error = str(exc) or "Ordner konnte nicht gelesen werden"
        self.signals.completed.emit(self.path, self.generation, count, error)


class FolderCountService(QtCore.QObject):
    """Deduplicate and bound direct-child folder counts for one canvas."""

    result_ready = QtCore.Signal(str, int, str)

    def __init__(self, parent: QtCore.QObject | None = None, max_workers: int = 2) -> None:
        super().__init__(parent)
        self._pool = QtCore.QThreadPool(self)
        self._pool.setMaxThreadCount(max(1, int(max_workers)))
        self._pending: set[str] = set()
        self._tasks: dict[str, _FolderCountTask] = {}
        self._cache: dict[str, tuple[float, tuple[int, int] | None, int, str]] = {}
        self._generations: dict[str, int] = {}
        self._cache_seconds = 5.0
        self._accept_results = True

    @property
    def max_workers(self) -> int:
        return self._pool.maxThreadCount()

    def request(self, path: str) -> None:
        if not self._accept_results:
            return
        normalized = os.path.abspath(os.path.expanduser(path))
        signature = self._directory_signature(normalized)
        cached = self._cache.get(normalized)
        if (
            cached is not None
            and time.monotonic() - cached[0] <= self._cache_seconds
            and cached[1] == signature
        ):
            _, _, count, error = cached
            QtCore.QTimer.singleShot(
                0,
                lambda p=normalized, c=count, e=error: self.result_ready.emit(p, c, e),
            )
            return
        if normalized in self._pending:
            return

        self._pending.add(normalized)
        generation = self._generations.get(normalized, 0)
        task = _FolderCountTask(normalized, generation)
        task.signals.completed.connect(self._on_completed)
        self._tasks[normalized] = task
        self._pool.start(task)

    @staticmethod
    def _directory_signature(path: str) -> tuple[int, int] | None:
        try:
            stat_result = os.stat(path, follow_symlinks=False)
        except OSError:
            return None
        return (stat_result.st_mtime_ns, stat_result.st_size)

    @QtCore.Slot(str, int, int, str)
    def _on_completed(self, path: str, generation: int, count: int, error: str) -> None:
        self._pending.discard(path)
        self._tasks.pop(path, None)
        if not self._accept_results or generation != self._generations.get(path, 0):
            return
        self._cache[path] = (
            time.monotonic(),
            self._directory_signature(path),
            count,
            error,
        )
        self.result_ready.emit(path, count, error)

    def invalidate(self, path: str | None = None) -> None:
        if path is None:
            self._cache.clear()
            for normalized in set(self._generations) | self._pending:
                self._generations[normalized] = self._generations.get(normalized, 0) + 1
            return
        normalized = os.path.abspath(os.path.expanduser(path))
        self._cache.pop(normalized, None)
        self._generations[normalized] = self._generations.get(normalized, 0) + 1

    def shutdown(self) -> None:
        self._accept_results = False
        self._pool.clear()
        self._pending.clear()
        self._tasks.clear()
