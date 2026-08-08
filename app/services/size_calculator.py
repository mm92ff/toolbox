#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Non-blocking, cancellable total-size calculation for toolbox tabs."""

from __future__ import annotations

import os
import stat
import threading
import time
from pathlib import Path
from typing import Iterable

from PySide6 import QtCore


def format_size(total_size: int, approximate: bool = False) -> str:
    if total_size < 1024:
        text = f"{total_size} B"
    elif total_size < 1024 * 1024:
        text = f"{total_size / 1024:.1f} KiB"
    elif total_size < 1024 * 1024 * 1024:
        text = f"{total_size / (1024 * 1024):.1f} MiB"
    else:
        text = f"{total_size / (1024 * 1024 * 1024):.1f} GiB"
    return f"≥ {text} (geschätzt)" if approximate else text


def calculate_paths_size(
    raw_paths: Iterable[str],
    cancelled: threading.Event | None = None,
    timeout_seconds: float = 1.5,
) -> str | None:
    """Calculate a deduplicated size snapshot; return ``None`` when cancelled."""

    cancel_event = cancelled or threading.Event()
    deadline = time.monotonic() + max(0.01, float(timeout_seconds))
    total_size = 0
    approximate = False
    readable_target_found = False
    seen_paths: set[str] = set()
    directory_roots: list[Path] = []

    normalized_paths: list[Path] = []
    for raw_path in raw_paths:
        text = (raw_path or "").strip()
        if not text:
            continue
        path = Path(os.path.abspath(os.path.expanduser(text)))
        key = os.path.normcase(str(path))
        if key in seen_paths:
            continue
        seen_paths.add(key)
        normalized_paths.append(path)
    normalized_paths.sort(key=lambda item: (len(item.parts), str(item)))

    for path in normalized_paths:
        if cancel_event.is_set():
            return None
        if time.monotonic() >= deadline:
            approximate = True
            break
        if any(path == root or path.is_relative_to(root) for root in directory_roots):
            continue

        try:
            path_stat = os.stat(path, follow_symlinks=False)
        except OSError:
            continue
        if stat.S_ISREG(path_stat.st_mode):
            readable_target_found = True
            total_size += path_stat.st_size
            continue
        if not stat.S_ISDIR(path_stat.st_mode):
            continue

        readable_target_found = True
        directory_roots.append(path)
        pending = [str(path)]
        while pending:
            if cancel_event.is_set():
                return None
            if time.monotonic() >= deadline:
                approximate = True
                pending.clear()
                break
            current = pending.pop()
            try:
                with os.scandir(current) as entries:
                    for entry in entries:
                        if cancel_event.is_set():
                            return None
                        if time.monotonic() >= deadline:
                            approximate = True
                            pending.clear()
                            break
                        try:
                            if entry.is_symlink():
                                continue
                            if entry.is_file(follow_symlinks=False):
                                total_size += entry.stat(follow_symlinks=False).st_size
                            elif entry.is_dir(follow_symlinks=False):
                                pending.append(entry.path)
                        except OSError:
                            continue
            except OSError:
                approximate = True
                continue

    if normalized_paths and not readable_target_found and not approximate:
        return "Nicht verfügbar"
    return format_size(total_size, approximate)


class _SizeTaskSignals(QtCore.QObject):
    completed = QtCore.Signal(int, str, object)


class _SizeTask(QtCore.QRunnable):
    def __init__(self, request_id: int, tab_id: str, paths: tuple[str, ...]) -> None:
        super().__init__()
        self.request_id = request_id
        self.tab_id = tab_id
        self.paths = paths
        self.cancelled = threading.Event()
        self.signals = _SizeTaskSignals()

    def run(self) -> None:
        result = calculate_paths_size(self.paths, self.cancelled)
        self.signals.completed.emit(self.request_id, self.tab_id, result)


class TabSizeCalculationService(QtCore.QObject):
    """Own request generations without owning short-lived ``QThread`` objects."""

    result_ready = QtCore.Signal(str, str)

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._pool = QtCore.QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self._request_id = 0
        self._tasks: dict[int, _SizeTask] = {}
        self._accept_results = True

    @property
    def max_workers(self) -> int:
        return self._pool.maxThreadCount()

    def request(self, tab_id: str, paths: tuple[str, ...]) -> None:
        if not self._accept_results:
            return
        self.cancel()
        self._request_id += 1
        task = _SizeTask(self._request_id, tab_id, paths)
        task.signals.completed.connect(self._on_completed)
        self._tasks[task.request_id] = task
        self._pool.start(task)

    def cancel(self) -> None:
        for task in self._tasks.values():
            task.cancelled.set()

    @QtCore.Slot(int, str, object)
    def _on_completed(self, request_id: int, tab_id: str, result: object) -> None:
        self._tasks.pop(request_id, None)
        if not self._accept_results or request_id != self._request_id or not isinstance(result, str):
            return
        self.result_ready.emit(tab_id, result)

    def shutdown(self) -> None:
        self._accept_results = False
        self.cancel()
        self._pool.clear()
