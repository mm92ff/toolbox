#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verified installation of the optional internal FFmpeg toolset."""

from __future__ import annotations

import hashlib
import os
import platform
import stat
import tarfile
import tempfile
import threading
import urllib.request
from pathlib import Path
from pathlib import PurePosixPath
from typing import BinaryIO, Callable

from PySide6 import QtCore


FFMPEG_VERSION = "7.0.2"
LINUX_X86_64_URL = (
    "https://github.com/mm92ff/toolbox/releases/download/v0.45-beta/"
    "Toolbox-0.45-beta-ffmpeg-7.0.2-linux-x86_64.tar.xz"
)
EXPECTED_ARCHIVE_SHA256 = "ba916b084e2aa7051500b94ccb01da1a6c03a4f3a054f8758578b9c8d38d9853"
EXPECTED_BINARY_SHA256 = {
    "ffmpeg": "080d5baae7e66281a31b04456049b8c6f83bf5aea95d3f72b4db7f9554f3e80a",
    "ffprobe": "f4380875a06580ad62671a63c79521f0913b8e80c4abc8a5461c59fac55ae3b2",
}
EXPECTED_ARCHIVE_FILES = frozenset(
    {*EXPECTED_BINARY_SHA256, "COPYING.LGPLv2.1", "README.md"}
)
MAX_ARCHIVE_BYTES = 150 * 1024 * 1024
MAX_BINARY_BYTES = 120 * 1024 * 1024


def _user_data_root() -> Path:
    configured = os.environ.get("XDG_DATA_HOME", "").strip()
    base = Path(configured).expanduser() if configured else Path.home() / ".local" / "share"
    return base / "toolbox" / "ffmpeg"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_limited(
    source: BinaryIO,
    target: Path,
    maximum: int,
    cancelled: threading.Event,
) -> None:
    written = 0
    with target.open("wb") as destination:
        while True:
            if cancelled.is_set():
                raise RuntimeError("FFmpeg installation was cancelled.")
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            written += len(chunk)
            if written > maximum:
                raise RuntimeError(f"Extracted file exceeds the {maximum}-byte safety limit.")
            destination.write(chunk)


def _download_archive(
    url: str,
    target: Path,
    progress_callback: Callable[[int, int], None] | None,
    cancelled: threading.Event,
) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "Toolbox-FFmpeg-Installer/1"})
    with urllib.request.urlopen(request, timeout=30) as response, target.open("wb") as output:
        declared_size = int(response.headers.get("Content-Length", "0") or 0)
        if declared_size > MAX_ARCHIVE_BYTES:
            raise RuntimeError("FFmpeg archive exceeds the configured download size limit.")
        downloaded = 0
        while True:
            if cancelled.is_set():
                raise RuntimeError("FFmpeg installation was cancelled.")
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            downloaded += len(chunk)
            if downloaded > MAX_ARCHIVE_BYTES:
                raise RuntimeError("FFmpeg download exceeds the configured size limit.")
            output.write(chunk)
            if progress_callback is not None:
                progress_callback(downloaded, declared_size)


def _extract_verified_binaries(
    archive: Path,
    output_dir: Path,
    cancelled: threading.Event,
) -> None:
    found: set[str] = set()
    with tarfile.open(archive, "r:xz") as tar:
        for member in tar:
            if cancelled.is_set():
                raise RuntimeError("FFmpeg installation was cancelled.")
            member_path = PurePosixPath(member.name)
            name = member_path.name
            if name not in EXPECTED_ARCHIVE_FILES:
                continue
            if member_path.is_absolute() or ".." in member_path.parts:
                raise RuntimeError(f"Unsafe archive path for '{name}'.")
            if name in found:
                raise RuntimeError(f"Duplicate '{name}' member in FFmpeg archive.")
            if not member.isfile() or member.issym() or member.islnk():
                raise RuntimeError(f"Unsafe archive member for '{name}'.")
            source = tar.extractfile(member)
            if source is None:
                raise RuntimeError(f"Could not read '{name}' from FFmpeg archive.")
            _copy_limited(source, output_dir / name, MAX_BINARY_BYTES, cancelled)
            found.add(name)

    missing = set(EXPECTED_ARCHIVE_FILES) - found
    if missing:
        raise RuntimeError(f"FFmpeg archive is missing: {', '.join(sorted(missing))}.")
    for name, expected_hash in EXPECTED_BINARY_SHA256.items():
        candidate = output_dir / name
        actual_hash = _sha256(candidate)
        if actual_hash != expected_hash:
            raise RuntimeError(
                f"SHA-256 mismatch for {name}: expected {expected_hash}, got {actual_hash}."
            )
        candidate.chmod(candidate.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _existing_install_is_valid(install_dir: Path) -> bool:
    return all((install_dir / name).is_file() for name in EXPECTED_ARCHIVE_FILES) and all(
        (install_dir / name).is_file() and _sha256(install_dir / name) == expected
        for name, expected in EXPECTED_BINARY_SHA256.items()
    )


def download_and_extract_ffmpeg(
    progress_callback: Callable[[int, int], None] | None = None,
    *,
    archive_source: Path | None = None,
    data_root: Path | None = None,
    cancelled: threading.Event | None = None,
) -> Path:
    """Install the pinned LGPL Linux x86_64 FFmpeg build and its notices."""

    cancel_event = cancelled or threading.Event()
    if platform.system() != "Linux" or platform.machine().lower() not in {"x86_64", "amd64"}:
        raise RuntimeError("The verified internal FFmpeg installer supports Linux x86_64 only.")

    root = data_root or _user_data_root()
    root.mkdir(parents=True, exist_ok=True)
    install_dir = root / FFMPEG_VERSION
    if install_dir.exists():
        if _existing_install_is_valid(install_dir):
            return install_dir / "ffmpeg"
        raise RuntimeError(
            f"Existing FFmpeg installation failed verification: {install_dir}. Remove it first."
        )

    with tempfile.TemporaryDirectory(prefix=".ffmpeg-install-", dir=str(root)) as temporary:
        temporary_dir = Path(temporary)
        archive = temporary_dir / "ffmpeg.tar.xz"
        if archive_source is not None:
            source_size = archive_source.stat().st_size
            if source_size > MAX_ARCHIVE_BYTES:
                raise RuntimeError("FFmpeg archive exceeds the configured size limit.")
            with archive_source.open("rb") as source:
                _copy_limited(source, archive, MAX_ARCHIVE_BYTES, cancel_event)
        else:
            _download_archive(LINUX_X86_64_URL, archive, progress_callback, cancel_event)
        archive_hash = _sha256(archive)
        if archive_hash != EXPECTED_ARCHIVE_SHA256:
            raise RuntimeError(
                "SHA-256 mismatch for FFmpeg archive: "
                f"expected {EXPECTED_ARCHIVE_SHA256}, got {archive_hash}."
            )
        if progress_callback is not None:
            progress_callback(-1, -1)

        staged = temporary_dir / FFMPEG_VERSION
        staged.mkdir()
        _extract_verified_binaries(archive, staged, cancel_event)
        if cancel_event.is_set():
            raise RuntimeError("FFmpeg installation was cancelled.")
        os.replace(staged, install_dir)

    return install_dir / "ffmpeg"


class FfmpegDownloadSignals(QtCore.QObject):
    progress = QtCore.Signal(int, int)
    finished_success = QtCore.Signal(str)
    finished_error = QtCore.Signal(str)


class FfmpegDownloadTask(QtCore.QRunnable):
    def __init__(self) -> None:
        super().__init__()
        self.signals = FfmpegDownloadSignals()
        self.cancelled = threading.Event()

    def cancel(self) -> None:
        self.cancelled.set()

    def run(self) -> None:
        try:
            path = download_and_extract_ffmpeg(
                progress_callback=lambda downloaded, total: self.signals.progress.emit(
                    downloaded, total
                ),
                cancelled=self.cancelled,
            )
            self.signals.finished_success.emit(str(path))
        except (OSError, RuntimeError, tarfile.TarError) as exc:
            self.signals.finished_error.emit(str(exc))
