#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Safely extract AppImage icons as data without executing the AppImage runtime."""

from __future__ import annotations

import hashlib
import logging
import mmap
import os
from pathlib import Path
import selectors
import signal
import struct
import subprocess
import tempfile
import threading
import time

from PySide6 import QtCore, QtGui

from app.services.system_utils import external_process_environment


logger = logging.getLogger(__name__)

_SQUASHFS_MAGIC = 0x73717368
_SQUASHFS_SUPERBLOCK = struct.Struct("<5I6H8Q")
_MAX_MAGIC_CANDIDATES = 128
_MAX_ICON_BYTES = 8 * 1024 * 1024
_MAX_ICON_PIXELS = 16 * 1024 * 1024
_MAX_CACHE_DIMENSION = 512
_EXTRACTION_TIMEOUT_SECONDS = 5.0


def is_appimage_path(path: str | Path) -> bool:
    return Path(path).suffix.casefold() == ".appimage"


def _normalized_path(path: str | Path) -> Path:
    return Path(os.path.abspath(os.path.expanduser(str(path))))


def _file_signature(path: Path) -> tuple[int, int] | None:
    try:
        stat_result = path.stat()
    except OSError:
        return None
    if not path.is_file():
        return None
    return stat_result.st_mtime_ns, stat_result.st_size


def appimage_icon_cache_directory() -> Path:
    xdg_cache_home = os.environ.get("XDG_CACHE_HOME", "").strip()
    cache_root = (
        Path(xdg_cache_home).expanduser()
        if xdg_cache_home
        else Path.home() / ".cache"
    )
    return cache_root / "toolbox" / "appimage_icons_static"


def _cache_path(
    path: Path,
    signature: tuple[int, int],
    cache_dir: Path,
) -> Path:
    mtime_ns, size = signature
    digest = hashlib.sha256(
        f"{path}\0{mtime_ns}\0{size}".encode("utf-8", errors="surrogateescape")
    ).hexdigest()
    return cache_dir / f"{digest}.png"


def _legacy_cache_path(path: Path) -> Path:
    # The MD5 value is only a compatibility filename, never a trust decision.
    digest = hashlib.md5(  # noqa: S324
        str(path).encode("utf-8", errors="surrogateescape"),
        usedforsecurity=False,
    ).hexdigest()
    return Path.home() / ".cache" / "toolbox" / "appimage_icons" / f"{digest}.png"


def cached_appimage_icon_path(
    raw_path: str | Path,
    *,
    cache_dir: Path | None = None,
    include_legacy: bool = True,
) -> str:
    """Return a current cached icon without inspecting AppImage contents."""

    path = _normalized_path(raw_path)
    if not is_appimage_path(path):
        return ""
    signature = _file_signature(path)
    if signature is None:
        return ""
    candidate = _cache_path(path, signature, cache_dir or appimage_icon_cache_directory())
    if candidate.is_file():
        return str(candidate)

    if not include_legacy:
        return ""
    legacy = _legacy_cache_path(path)
    try:
        if legacy.is_file() and legacy.stat().st_mtime_ns >= signature[0]:
            return str(legacy)
    except OSError:
        return ""
    return ""


def _valid_squashfs_superblock(
    mapped: mmap.mmap,
    offset: int,
    file_size: int,
) -> bool:
    if offset < 0 or offset + _SQUASHFS_SUPERBLOCK.size > file_size:
        return False
    try:
        values = _SQUASHFS_SUPERBLOCK.unpack_from(mapped, offset)
    except (ValueError, struct.error):
        return False
    magic = values[0]
    block_size = values[3]
    block_log = values[6]
    major = values[9]
    minor = values[10]
    bytes_used = values[12]
    if magic != _SQUASHFS_MAGIC or major != 4 or minor != 0:
        return False
    if block_size < 4096 or block_size > 1024 * 1024:
        return False
    if block_size & (block_size - 1) or block_log != block_size.bit_length() - 1:
        return False
    if bytes_used < _SQUASHFS_SUPERBLOCK.size or offset + bytes_used > file_size:
        return False
    return True


def find_squashfs_offset(path: str | Path) -> int | None:
    """Find a validated SquashFS 4 superblock by reading the file as passive data."""

    candidate_path = _normalized_path(path)
    try:
        file_size = candidate_path.stat().st_size
        if file_size < _SQUASHFS_SUPERBLOCK.size:
            return None
        with candidate_path.open("rb") as stream, mmap.mmap(
            stream.fileno(),
            0,
            access=mmap.ACCESS_READ,
        ) as mapped:
            search_from = 0
            for _ in range(_MAX_MAGIC_CANDIDATES):
                offset = mapped.find(b"hsqs", search_from)
                if offset < 0:
                    return None
                if _valid_squashfs_superblock(mapped, offset, file_size):
                    return offset
                search_from = offset + 4
    except (OSError, ValueError):
        return None
    return None


def _trusted_unsquashfs() -> str:
    for candidate in (Path("/usr/bin/unsquashfs"), Path("/bin/unsquashfs")):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return ""


def _terminate_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except OSError:
        process.kill()


def _read_icon_with_unsquashfs(
    appimage_path: Path,
    offset: int,
    extractor: str,
    cancelled: threading.Event,
) -> bytes:
    command = [
        extractor,
        "-no-progress",
        "-processors",
        "1",
        "-offset",
        str(offset),
        "-cat",
        str(appimage_path),
        ".DirIcon",
    ]
    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=external_process_environment(extractor),
        start_new_session=True,
    )
    if process.stdout is None:
        _terminate_process(process)
        return b""

    output = bytearray()
    deadline = time.monotonic() + _EXTRACTION_TIMEOUT_SECONDS
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)
    try:
        while True:
            if cancelled.is_set() or time.monotonic() >= deadline:
                _terminate_process(process)
                return b""
            events = selector.select(timeout=0.1)
            if not events:
                if process.poll() is not None:
                    break
                continue
            chunk = os.read(process.stdout.fileno(), 64 * 1024)
            if not chunk:
                break
            output.extend(chunk)
            if len(output) > _MAX_ICON_BYTES:
                _terminate_process(process)
                return b""
        remaining = max(0.01, deadline - time.monotonic())
        try:
            return_code = process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            _terminate_process(process)
            return b""
        return bytes(output) if return_code == 0 else b""
    finally:
        selector.close()
        if process.poll() is None:
            _terminate_process(process)
        process.stdout.close()


def _write_sanitized_png(icon_data: bytes, output_path: Path) -> bool:
    if not icon_data or len(icon_data) > _MAX_ICON_BYTES:
        return False
    byte_array = QtCore.QByteArray(icon_data)
    buffer = QtCore.QBuffer(byte_array)
    if not buffer.open(QtCore.QIODevice.OpenModeFlag.ReadOnly):
        return False
    reader = QtGui.QImageReader(buffer)
    reader.setDecideFormatFromContent(True)
    size = reader.size()
    if not size.isValid() or size.width() <= 0 or size.height() <= 0:
        return False
    if size.width() * size.height() > _MAX_ICON_PIXELS:
        return False
    scaled_size = size.scaled(
        _MAX_CACHE_DIMENSION,
        _MAX_CACHE_DIMENSION,
        QtCore.Qt.AspectRatioMode.KeepAspectRatio,
    )
    if scaled_size != size:
        reader.setScaledSize(scaled_size)
    image = reader.read()
    if image.isNull():
        return False

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        output_path.parent.chmod(0o700)
    except OSError:
        pass
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".appimage-icon-",
        suffix=".png",
        dir=str(output_path.parent),
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        if not image.save(str(temporary_path), "PNG"):
            return False
        temporary_path.chmod(0o600)
        os.replace(temporary_path, output_path)
        return True
    except OSError:
        return False
    finally:
        temporary_path.unlink(missing_ok=True)


def extract_appimage_icon_static(
    raw_path: str | Path,
    *,
    cache_dir: Path | None = None,
    extractor: str | None = None,
    cancelled: threading.Event | None = None,
) -> str:
    """Extract and rasterize ``.DirIcon`` without launching the AppImage."""

    path = _normalized_path(raw_path)
    if not is_appimage_path(path):
        return ""
    signature = _file_signature(path)
    if signature is None:
        return ""
    target_dir = cache_dir or appimage_icon_cache_directory()
    output_path = _cache_path(path, signature, target_dir)
    if output_path.is_file():
        return str(output_path)

    extraction_program = extractor or _trusted_unsquashfs()
    if not extraction_program:
        return ""
    offset = find_squashfs_offset(path)
    if offset is None:
        return ""
    cancel_event = cancelled or threading.Event()
    try:
        icon_data = _read_icon_with_unsquashfs(
            path,
            offset,
            extraction_program,
            cancel_event,
        )
    except OSError as exc:
        logger.debug("Static AppImage icon extraction failed for '%s': %s", path.name, exc)
        return ""
    if cancel_event.is_set() or _file_signature(path) != signature:
        return ""
    if not _write_sanitized_png(icon_data, output_path):
        return ""
    return str(output_path)


class _AppImageIconSignals(QtCore.QObject):
    completed = QtCore.Signal(str, object, str)


class _AppImageIconTask(QtCore.QRunnable):
    def __init__(self, path: str, signature: tuple[int, int], cache_dir: Path) -> None:
        super().__init__()
        self.path = path
        self.signature = signature
        self.cache_dir = cache_dir
        self.cancelled = threading.Event()
        self.signals = _AppImageIconSignals()

    def run(self) -> None:
        icon_path = extract_appimage_icon_static(
            self.path,
            cache_dir=self.cache_dir,
            cancelled=self.cancelled,
        )
        self.signals.completed.emit(self.path, self.signature, icon_path)


class AppImageIconService(QtCore.QObject):
    """Deduplicate and bound static AppImage icon extraction jobs."""

    result_ready = QtCore.Signal(str, str)

    def __init__(
        self,
        parent: QtCore.QObject | None = None,
        *,
        cache_dir: Path | None = None,
    ) -> None:
        super().__init__(parent)
        self._cache_dir = cache_dir or appimage_icon_cache_directory()
        self._pool = QtCore.QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self._tasks: dict[str, _AppImageIconTask] = {}
        self._negative_cache: dict[tuple[str, tuple[int, int]], float] = {}
        self._accept_results = True

    @property
    def max_workers(self) -> int:
        return self._pool.maxThreadCount()

    def request(self, raw_path: str | Path) -> None:
        if not self._accept_results or not is_appimage_path(raw_path):
            return
        path = _normalized_path(raw_path)
        signature = _file_signature(path)
        if signature is None:
            return
        path_text = str(path)
        cached = cached_appimage_icon_path(
            path,
            cache_dir=self._cache_dir,
        )
        if cached:
            QtCore.QTimer.singleShot(
                0,
                lambda p=path_text, i=cached: self.result_ready.emit(p, i),
            )
            return
        if path_text in self._tasks:
            return
        failure_time = self._negative_cache.get((path_text, signature))
        if failure_time is not None and time.monotonic() - failure_time < 30.0:
            return

        task = _AppImageIconTask(path_text, signature, self._cache_dir)
        task.signals.completed.connect(self._on_completed)
        self._tasks[path_text] = task
        self._pool.start(task)

    @QtCore.Slot(str, object, str)
    def _on_completed(
        self,
        path: str,
        signature_object: object,
        icon_path: str,
    ) -> None:
        self._tasks.pop(path, None)
        signature = signature_object if isinstance(signature_object, tuple) else None
        if not self._accept_results or signature is None:
            return
        if _file_signature(Path(path)) != signature:
            return
        if icon_path:
            self._negative_cache.pop((path, signature), None)
            self.result_ready.emit(path, icon_path)
        else:
            self._negative_cache[(path, signature)] = time.monotonic()

    def shutdown(self) -> None:
        self._accept_results = False
        for task in self._tasks.values():
            task.cancelled.set()
        self._pool.clear()
        self._tasks.clear()
