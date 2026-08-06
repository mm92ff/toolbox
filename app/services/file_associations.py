#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""File association service: open files with configured or system default programs."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path

from app import constants


def _extension_group(path: str) -> str | None:
    """Return which group a file path belongs to, or None if unrecognised."""
    ext = Path(path).suffix.lower()
    if ext in constants.FILE_ASSOC_AUDIO_EXTENSIONS:
        return "audio"
    if ext in constants.FILE_ASSOC_VIDEO_EXTENSIONS:
        return "video"
    if ext in constants.FILE_ASSOC_IMAGE_EXTENSIONS:
        return "image"
    if ext in constants.FILE_ASSOC_PDF_EXTENSIONS:
        return "pdf"
    if ext in constants.FILE_ASSOC_DOCUMENT_EXTENSIONS:
        return "document"
    return None


def open_with_file_associations(
    path: str,
    use_system: bool,
    audio_app: str,
    video_app: str,
    image_app: str,
    pdf_app: str,
    document_app: str,
) -> bool:
    """Open a file using configured associations. Returns True if handled."""
    group = _extension_group(path)
    if group is None:
        return False

    if use_system:
        return _open_with_system(path)

    app_map = {
        "audio": audio_app.strip(),
        "video": video_app.strip(),
        "image": image_app.strip(),
        "pdf": pdf_app.strip(),
        "document": document_app.strip(),
    }
    custom_app = app_map.get(group, "").strip()
    if not custom_app:
        # Fallback to system if no custom app configured
        return _open_with_system(path)
    return _open_with_custom(custom_app, path)


def _open_with_system(path: str) -> bool:
    """Open file using the OS default application."""
    try:
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return True
    except (OSError, FileNotFoundError):
        return False


def _open_with_custom(app: str, path: str) -> bool:
    """Open file using a custom application command."""
    try:
        # Support e.g. 'vlc' or '/usr/bin/vlc' or even 'flatpak run org.videolan.VLC'
        parts = shlex.split(app)
        parts.append(path)
        subprocess.Popen(parts)
        return True
    except (OSError, FileNotFoundError, ValueError):
        return False
