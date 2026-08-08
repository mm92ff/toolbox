#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""File association service: open files with configured or system default programs."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from app import constants
from app.services.system_utils import external_process_environment


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
    normalized_path = str(Path(path).expanduser().resolve(strict=False))
    group = _extension_group(normalized_path)
    if group is None:
        return False

    if use_system:
        return _open_with_system(normalized_path)

    app_map = {
        "audio": audio_app.strip(),
        "video": video_app.strip(),
        "image": image_app.strip(),
        "pdf": pdf_app.strip(),
        "document": document_app.strip(),
    }
    custom_app = app_map.get(group, "").strip()
    if not custom_app:
        raise OSError(
            f"No custom application is configured for {group} files. "
            "Choose an application or enable the system default."
        )
    return _open_with_custom(custom_app, normalized_path)


def _open_with_system(path: str) -> bool:
    """Open file using the OS default application."""
    try:
        if sys.platform == "win32":
            os.startfile(path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            executable = shutil.which("open")
            if not executable:
                raise FileNotFoundError("The system command 'open' is unavailable.")
            subprocess.Popen(
                [executable, path],
                shell=False,
                env=external_process_environment(executable),
            )
        else:
            executable = shutil.which("xdg-open")
            command = [executable, path] if executable else []
            if not command:
                executable = shutil.which("gio")
                command = [executable, "open", path] if executable else []
            if not command or not executable:
                raise FileNotFoundError("The system command 'xdg-open' or 'gio' is unavailable.")
            subprocess.Popen(
                command,
                shell=False,
                env=external_process_environment(executable),
            )
        return True
    except (OSError, FileNotFoundError) as exc:
        raise OSError(f"Could not open '{Path(path).name}' with the system default: {exc}") from exc


def _open_with_custom(app: str, path: str) -> bool:
    """Open file using a custom application command."""
    try:
        parts = shlex.split(app)
        if not parts:
            raise ValueError("The custom application command is empty.")
        raw_executable = parts[0]
        if os.path.sep in raw_executable or (os.path.altsep and os.path.altsep in raw_executable):
            executable_path = Path(raw_executable).expanduser().resolve(strict=False)
            if not executable_path.is_file():
                raise FileNotFoundError(raw_executable)
            executable = str(executable_path)
        else:
            executable = shutil.which(raw_executable)
            if not executable:
                raise FileNotFoundError(raw_executable)
        parts[0] = executable
        parts.append(path)
        subprocess.Popen(
            parts,
            shell=False,
            env=external_process_environment(executable),
        )
        return True
    except (OSError, FileNotFoundError, ValueError) as exc:
        raise OSError(f"Could not start custom application '{app}': {exc}") from exc
