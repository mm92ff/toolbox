#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Service to download and install a local copy of FFmpeg."""

from __future__ import annotations

import os
import stat
import tarfile
import tempfile
import urllib.request
import platform
import zipfile
from pathlib import Path
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def download_and_extract_ffmpeg(
    progress_callback: Callable[[int, int], None] | None = None
) -> Path:
    """
    Downloads static FFmpeg for Linux, extracts it, and places it into PROJECT_ROOT/.bin/
    Returns the path to the ffmpeg executable.
    """
    bin_dir = Path(PROJECT_ROOT) / ".bin"
    bin_dir.mkdir(parents=True, exist_ok=True)

    def reporthook(block_num: int, block_size: int, total_size: int) -> None:
        if progress_callback:
            downloaded = block_num * block_size
            progress_callback(downloaded, total_size)

    with tempfile.TemporaryDirectory() as tmpdir:
        is_windows = platform.system() == "Windows"
        
        if is_windows:
            url = "https://github.com/GyanD/codexffmpeg/releases/download/2024-03-24-git-b9c6a782a6/ffmpeg-2024-03-24-git-b9c6a782a6-essentials_build.zip"
            archive_name = "ffmpeg.zip"
            ffmpeg_target = bin_dir / "ffmpeg.exe"
            ffprobe_target = bin_dir / "ffprobe.exe"
        else:
            url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
            archive_name = "ffmpeg.tar.xz"
            ffmpeg_target = bin_dir / "ffmpeg"
            ffprobe_target = bin_dir / "ffprobe"
            
        archive_path = Path(tmpdir) / archive_name
        
        # 1. Download
        urllib.request.urlretrieve(url, archive_path, reporthook=reporthook)
        
        # 2. Extract
        if progress_callback:
            # Signal extraction phase
            progress_callback(-1, -1)
            
        if is_windows:
            with zipfile.ZipFile(archive_path, "r") as zipf:
                for member in zipf.namelist():
                    if member.endswith("/ffmpeg.exe") or member == "ffmpeg.exe":
                        extracted_path = zipf.extract(member, path=tmpdir)
                        Path(extracted_path).replace(ffmpeg_target)
                    elif member.endswith("/ffprobe.exe") or member == "ffprobe.exe":
                        extracted_path = zipf.extract(member, path=tmpdir)
                        Path(extracted_path).replace(ffprobe_target)
        else:
            with tarfile.open(archive_path, "r:xz") as tar:
                for member in tar.getmembers():
                    if member.name.endswith("/ffmpeg") or member.name == "ffmpeg":
                        member.name = "ffmpeg"  # Flatten
                        tar.extract(member, path=bin_dir)
                    elif member.name.endswith("/ffprobe") or member.name == "ffprobe":
                        member.name = "ffprobe" # Flatten
                        tar.extract(member, path=bin_dir)

    # 3. Make executable (Linux only, Windows ignores this)
    for target in [ffmpeg_target, ffprobe_target]:
        if target.exists() and not is_windows:
            st = os.stat(target)
            os.chmod(target, st.st_mode | stat.S_IEXEC)
            
    if not ffmpeg_target.exists():
        raise RuntimeError("FFmpeg executable not found after extraction.")
        
    return ffmpeg_target


from PySide6 import QtCore

class FfmpegDownloadThread(QtCore.QThread):
    progress = QtCore.Signal(int, int)
    finished_success = QtCore.Signal(str)
    finished_error = QtCore.Signal(str)

    def run(self) -> None:
        try:
            path = download_and_extract_ffmpeg(
                progress_callback=lambda d, t: self.progress.emit(d, t)
            )
            self.finished_success.emit(str(path))
        except Exception as e:
            self.finished_error.emit(str(e))

