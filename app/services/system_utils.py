#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Utility helpers for the toolbox launcher."""

from __future__ import annotations

import ctypes
from functools import lru_cache
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


@lru_cache(maxsize=2048)
def _path_log_label_cached(raw_path: str) -> str:
    path = Path(raw_path).expanduser()
    return path.name.strip() or str(path)


def _path_log_label(raw_path: str | Path) -> str:
    return _path_log_label_cached(str(raw_path))


def _sanitize_path_text(raw_path: str, field_name: str = "path") -> str:
    text = (raw_path or "").strip()
    if not text:
        raise ValueError(f"{field_name.capitalize()} must not be empty.")
    if "\x00" in text:
        raise ValueError(f"{field_name.capitalize()} contains an invalid null byte.")
    return text


def _resolve_system_command(command: str) -> str:
    executable = shutil.which(command)
    if executable:
        return executable
    raise FileNotFoundError(f"Required system command is not available: {command}")


def clear_system_utils_caches() -> None:
    """Clear bounded module caches used by system utility helpers."""
    _path_log_label_cached.cache_clear()


def ensure_writable_directory(directory: Path) -> None:
    """Ensure a directory exists and can be written to."""
    if directory.exists() and not directory.is_dir():
        raise OSError(f"Path is not a directory: {directory}")

    directory.mkdir(parents=True, exist_ok=True)

    probe_fd, probe_name = tempfile.mkstemp(
        prefix=".toolbox_write_probe_",
        suffix=".tmp",
        dir=str(directory),
    )
    os.close(probe_fd)
    probe_path = Path(probe_name)
    try:
        probe_path.write_text("ok", encoding="utf-8")
    except OSError as exc:
        raise OSError(f"Configuration directory is not writable: {directory}") from exc
    finally:
        try:
            probe_path.unlink(missing_ok=True)
        except OSError as exc:
            logger.debug(
                "Could not remove config directory probe file '%s': %s",
                _path_log_label(probe_path),
                exc,
            )


def get_config_directory(app_name: str) -> Path:
    """Return and create the OS-specific configuration directory."""
    safe_app_name = (
        "".join(char for char in app_name if char.isalnum() or char in "_-") or "ToolboxStarter"
    )

    if sys.platform == "win32":
        base = Path(os.getenv("APPDATA", str(Path.home() / "AppData" / "Roaming")))
        config_dir = base / safe_app_name
    elif sys.platform == "darwin":
        config_dir = Path.home() / "Library" / "Application Support" / safe_app_name
    else:
        config_dir = Path.home() / ".config" / safe_app_name

    ensure_writable_directory(config_dir)
    return config_dir


def normalize_tool_path(filepath: str) -> str:
    """Return a normalized, expanded path string for duplicate detection."""
    path = Path(filepath).expanduser()
    try:
        resolved = path.resolve(strict=False)
    except OSError:
        resolved = path

    normalized = str(resolved)
    if sys.platform == "win32":
        normalized = normalized.lower()
    return normalized


def display_name_from_path(filepath: str) -> str:
    """Return a user-facing display name derived from a file path."""
    path = Path(filepath)
    return path.stem or path.name or filepath


def open_directory_in_os(dirpath: str) -> bool:
    """Open a directory in the native file manager and report success."""
    try:
        directory = Path(_sanitize_path_text(dirpath, "directory path")).expanduser().resolve()
        if not directory.is_dir():
            return False

        if sys.platform == "win32":
            os.startfile(str(directory))
        elif sys.platform == "darwin":
            open_cmd = _resolve_system_command("open")
            subprocess.run([open_cmd, str(directory)], check=True, shell=False)
        else:
            xdg_open_cmd = _resolve_system_command("xdg-open")
            subprocess.run([xdg_open_cmd, str(directory)], check=True, shell=False)
        return True
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        AttributeError,
        OSError,
        ValueError,
    ) as exc:
        logger.debug(
            "Could not open directory '%s': %s",
            _path_log_label(dirpath),
            exc,
        )
        return False


def launch_path(
    filepath: str,
    run_as_admin: bool = False,
    arguments: str | None = None,
    working_directory: str | None = None,
    wait: bool = False,
    window_style: str = "normal",
) -> None:
    """Launch a file or folder with optional elevated and advanced launch options."""
    path = Path(_sanitize_path_text(filepath)).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    if path.is_dir():
        if open_directory_in_os(str(path)):
            return
        raise OSError(f"Could not open folder: {filepath}")

    normalized_window_style = _normalize_window_style(window_style)
    normalized_arguments = (arguments or "").strip() or None
    normalized_working_directory = None
    if working_directory is not None and working_directory.strip():
        normalized_working_directory = _sanitize_path_text(
            working_directory,
            "working directory",
        )
    has_advanced_options = bool(
        normalized_arguments
        or normalized_working_directory
        or wait
        or normalized_window_style != "normal"
    )

    if sys.platform == "win32":
        if has_advanced_options:
            _launch_windows_with_start_process(
                path,
                run_as_admin=run_as_admin,
                arguments=normalized_arguments,
                working_directory=normalized_working_directory,
                wait=wait,
                window_style=normalized_window_style,
            )
            return
        if run_as_admin:
            _launch_windows_admin(path)
            return

        if path.suffix.lower() != ".exe":
            os.startfile(str(path))
            return

        subprocess.Popen([str(path)], cwd=str(path.parent), shell=False)
        return

    if run_as_admin:
        raise OSError("'Run as administrator' is only supported on Windows.")

    if sys.platform == "darwin":
        open_cmd = _resolve_system_command("open")
        subprocess.Popen([open_cmd, str(path)], cwd=str(path.parent), shell=False)
        return

    subprocess.Popen([str(path)], cwd=str(path.parent), shell=False)


def _launch_windows_admin(path: Path) -> None:
    executable = path
    parameters: str | None = None
    working_directory = str(path.parent)

    if path.suffix.lower() == ".lnk":
        target_path, target_arguments, target_working_directory = _resolve_windows_shortcut(path)
        if target_path is not None:
            executable = target_path
            parameters = target_arguments
            if target_working_directory:
                working_directory = target_working_directory
            else:
                working_directory = str(target_path.parent)

    result = _shell_execute_windows(
        "runas",
        str(executable),
        parameters,
        working_directory,
        1,
    )
    if result <= 32:
        raise OSError(f"ShellExecuteW fehlgeschlagen: {result}")


def _normalize_window_style(window_style: str) -> str:
    style = (window_style or "normal").strip().lower()
    if style in {"normal", "minimized", "maximized", "hidden"}:
        return style
    return "normal"


def _merge_arguments(base_arguments: str | None, extra_arguments: str | None) -> str | None:
    base = (base_arguments or "").strip()
    extra = (extra_arguments or "").strip()
    if base and extra:
        return f"{base} {extra}"
    return base or extra or None


def _launch_windows_with_start_process(
    path: Path,
    run_as_admin: bool,
    arguments: str | None,
    working_directory: str | None,
    wait: bool,
    window_style: str,
) -> None:
    executable = path
    shortcut_arguments: str | None = None
    shortcut_working_directory: str | None = None
    if path.suffix.lower() == ".lnk":
        target_path, target_arguments, target_working_directory = _resolve_windows_shortcut(path)
        if target_path is not None:
            executable = target_path
            shortcut_arguments = target_arguments
            shortcut_working_directory = target_working_directory

    merged_arguments = _merge_arguments(shortcut_arguments, arguments)
    launch_working_directory = (
        working_directory or shortcut_working_directory or str(executable.parent)
    )
    ps_window_style = {
        "normal": "Normal",
        "minimized": "Minimized",
        "maximized": "Maximized",
        "hidden": "Hidden",
    }.get(window_style, "Normal")

    script = (
        "$ErrorActionPreference='Stop'; "
        "$params=@{FilePath=$env:TB_FILE}; "
        "if($env:TB_ARGS){$params['ArgumentList']=$env:TB_ARGS}; "
        "if($env:TB_WORKDIR){$params['WorkingDirectory']=$env:TB_WORKDIR}; "
        "if($env:TB_WINDOWSTYLE -and $env:TB_WINDOWSTYLE -ne 'Normal'){"
        "$params['WindowStyle']=$env:TB_WINDOWSTYLE}; "
        "if($env:TB_RUNAS -eq '1'){$params['Verb']='RunAs'}; "
        "if($env:TB_WAIT -eq '1'){"
        "  $p=Start-Process @params -PassThru; "
        "  $p.WaitForExit()"
        "} else {"
        "  Start-Process @params | Out-Null"
        "}"
    )
    env = os.environ.copy()
    env["TB_FILE"] = str(executable)
    env["TB_ARGS"] = merged_arguments or ""
    env["TB_WORKDIR"] = launch_working_directory or ""
    env["TB_RUNAS"] = "1" if run_as_admin else "0"
    env["TB_WAIT"] = "1" if wait else "0"
    env["TB_WINDOWSTYLE"] = ps_window_style

    try:
        powershell_cmd = _resolve_system_command("powershell")
        subprocess.run(
            [powershell_cmd, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
    except (FileNotFoundError, PermissionError, OSError, subprocess.CalledProcessError) as exc:
        error_text = ""
        if isinstance(exc, subprocess.CalledProcessError):
            error_text = (exc.stderr or exc.stdout or "").strip()
        raise OSError(error_text or "Start-Process failed.") from exc


def _shell_execute_windows(
    operation: str,
    filepath: str,
    parameters: str | None,
    working_directory: str | None,
    show_cmd: int,
) -> int:
    return ctypes.windll.shell32.ShellExecuteW(
        None,
        operation,
        filepath,
        parameters,
        working_directory,
        show_cmd,
    )


def _resolve_windows_shortcut(path: Path) -> tuple[Path | None, str | None, str | None]:
    if path.suffix.lower() != ".lnk":
        return None, None, None

    script = (
        "$ErrorActionPreference='Stop'; "
        "$shell=New-Object -ComObject WScript.Shell; "
        "$shortcut=$shell.CreateShortcut($env:TOOLBOX_SHORTCUT_PATH); "
        "[PSCustomObject]@{"
        "target=$shortcut.TargetPath;"
        "arguments=$shortcut.Arguments;"
        "working_directory=$shortcut.WorkingDirectory"
        "} | ConvertTo-Json -Compress"
    )

    env = os.environ.copy()
    env["TOOLBOX_SHORTCUT_PATH"] = str(path)
    try:
        powershell_cmd = _resolve_system_command("powershell")
        completed = subprocess.run(
            [powershell_cmd, "-NoProfile", "-Command", script],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
    except (FileNotFoundError, PermissionError, OSError, subprocess.CalledProcessError) as exc:
        logger.debug("Could not resolve Windows shortcut '%s': %s", _path_log_label(path), exc)
        return None, None, None

    raw_output = (completed.stdout or "").strip()
    if not raw_output:
        return None, None, None

    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        logger.debug(
            "Could not parse shortcut metadata JSON for '%s': %s",
            _path_log_label(path),
            exc,
        )
        return None, None, None

    if not isinstance(payload, dict):
        return None, None, None

    raw_target = str(payload.get("target") or "").strip()
    if not raw_target:
        return None, None, None

    expanded_target = os.path.expandvars(raw_target)
    target_path = Path(expanded_target).expanduser()

    arguments = str(payload.get("arguments") or "").strip() or None
    working_directory = str(payload.get("working_directory") or "").strip() or None
    return target_path, arguments, working_directory
