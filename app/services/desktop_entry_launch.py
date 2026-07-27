#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prepare and monitor Linux desktop-entry launches."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from pathlib import Path
import re
import selectors
import shutil
import subprocess
import threading
import time
from typing import Literal
import unicodedata

from PySide6 import QtCore

from app.services.desktop_entries import (
    DesktopEntryError,
    DesktopEntryMetadata,
    DesktopLaunchInput,
    expand_desktop_exec_many,
    read_desktop_entry,
)


logger = logging.getLogger(__name__)

MAX_CAPTURED_STDERR_BYTES = 64 * 1024
FAST_FAILURE_SECONDS = 2.0
LaunchMode = Literal["direct", "gio", "link"]
_ANSI_ESCAPE = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")


@dataclass(frozen=True, slots=True)
class PreparedDesktopLaunch:
    """One resolved desktop launch, possibly containing multiple commands."""

    metadata: DesktopEntryMetadata
    mode: LaunchMode
    commands: tuple[tuple[str, ...], ...]
    working_directory: Path


@dataclass(slots=True)
class _RunningLaunch:
    process: subprocess.Popen[bytes]
    source_path: str
    title: str
    mode: LaunchMode
    started_at: float


def _resolve_executable(
    executable: str,
    *,
    working_directory: Path,
    source_path: Path,
) -> str:
    if not executable:
        raise DesktopEntryError(f"{source_path.name}: executable is empty")
    candidate = Path(executable).expanduser()
    if candidate.is_absolute() or "/" in executable:
        if not candidate.is_absolute():
            candidate = working_directory / candidate
        candidate = candidate.resolve(strict=False)
        if not candidate.is_file():
            raise DesktopEntryError(
                f"{source_path.name}: executable not found: {executable}"
            )
        if not os.access(candidate, os.X_OK):
            raise DesktopEntryError(
                f"{source_path.name}: executable is not permitted: {executable}"
            )
        return str(candidate)
    resolved = shutil.which(executable)
    if not resolved:
        raise DesktopEntryError(
            f"{source_path.name}: executable not found in PATH: {executable}"
        )
    return resolved


def _resolve_working_directory(
    metadata: DesktopEntryMetadata,
    override: str | None,
) -> Path:
    raw_directory = (override or "").strip() or metadata.working_directory
    if raw_directory:
        directory = Path(raw_directory).expanduser()
        if not directory.is_absolute():
            directory = metadata.source_path.parent / directory
    else:
        directory = metadata.source_path.parent
    directory = directory.resolve(strict=False)
    if not directory.is_dir():
        raise DesktopEntryError(
            f"{metadata.source_path.name}: working directory not found: {directory}"
        )
    return directory


def _validate_try_exec(
    metadata: DesktopEntryMetadata,
    working_directory: Path,
) -> None:
    if not metadata.try_exec:
        return
    _resolve_executable(
        metadata.try_exec,
        working_directory=working_directory,
        source_path=metadata.source_path,
    )


def prepare_desktop_launch(
    filepath: str | Path,
    *,
    launch_input: DesktopLaunchInput | None = None,
    working_directory: str | None = None,
) -> PreparedDesktopLaunch:
    """Resolve a desktop entry to safe argv arrays without starting it."""

    metadata = read_desktop_entry(filepath)
    resolved_working_directory = _resolve_working_directory(metadata, working_directory)
    _validate_try_exec(metadata, resolved_working_directory)
    launch_input = launch_input or DesktopLaunchInput()

    if metadata.is_link:
        if launch_input.items:
            raise DesktopEntryError(
                f"{metadata.source_path.name}: link entries do not accept dropped inputs"
            )
        opener = shutil.which("xdg-open") or shutil.which("gio")
        if not opener:
            raise DesktopEntryError(
                f"{metadata.source_path.name}: xdg-open or gio is required"
            )
        command = (
            (opener, metadata.url)
            if Path(opener).name == "xdg-open"
            else (opener, "open", metadata.url)
        )
        return PreparedDesktopLaunch(
            metadata=metadata,
            mode="link",
            commands=(command,),
            working_directory=resolved_working_directory,
        )

    if metadata.terminal or metadata.dbus_activatable:
        # GIO performs the actual expansion, but Toolbox must still reject
        # malformed field codes, incompatible drops, and unsafe Exec syntax
        # before handing the request to the desktop system.
        if metadata.exec_line:
            expand_desktop_exec_many(metadata, launch_input)
        elif launch_input.items:
            raise DesktopEntryError(
                f"{metadata.source_path.name}: this desktop entry does not "
                "accept dropped files or URLs"
            )
        gio = shutil.which("gio")
        if not gio:
            raise DesktopEntryError(
                f"{metadata.source_path.name}: gio is required for this desktop entry"
            )
        gio_arguments = tuple(
            item.local_path or item.url for item in launch_input.items
        )
        return PreparedDesktopLaunch(
            metadata=metadata,
            mode="gio",
            commands=((gio, "launch", str(metadata.source_path), *gio_arguments),),
            working_directory=resolved_working_directory,
        )

    commands: list[tuple[str, ...]] = []
    for expanded in expand_desktop_exec_many(metadata, launch_input):
        executable = _resolve_executable(
            expanded[0],
            working_directory=resolved_working_directory,
            source_path=metadata.source_path,
        )
        commands.append((executable, *expanded[1:]))
    return PreparedDesktopLaunch(
        metadata=metadata,
        mode="direct",
        commands=tuple(commands),
        working_directory=resolved_working_directory,
    )


def _append_stderr_tail(buffer: bytearray, payload: bytes) -> bool:
    """Append bytes while retaining at most the configured stderr tail."""

    if not payload:
        return False
    was_truncated = len(buffer) + len(payload) > MAX_CAPTURED_STDERR_BYTES
    buffer.extend(payload)
    overflow = len(buffer) - MAX_CAPTURED_STDERR_BYTES
    if overflow > 0:
        del buffer[:overflow]
    return was_truncated


def _capture_stderr(process: subprocess.Popen[bytes]) -> tuple[bytes, bool]:
    """Drain stderr without blocking and retain only a bounded in-memory tail."""

    pipe = process.stderr
    if pipe is None:
        return b"", False

    buffer = bytearray()
    truncated = False
    selector = selectors.DefaultSelector()
    try:
        os.set_blocking(pipe.fileno(), False)
        selector.register(pipe, selectors.EVENT_READ)
        while True:
            for key, _events in selector.select(timeout=0.1):
                try:
                    chunk = os.read(key.fileobj.fileno(), 8192)
                except BlockingIOError:
                    continue
                if chunk:
                    truncated = _append_stderr_tail(buffer, chunk) or truncated
                else:
                    try:
                        selector.unregister(pipe)
                    except (KeyError, ValueError):
                        pass

            if not selector.get_map():
                process.wait()
                return bytes(buffer), truncated

            exit_code = process.poll()
            if exit_code is None:
                continue

            # The process has exited. Drain bytes already present in the pipe,
            # but do not wait for a detached descendant that inherited stderr.
            while True:
                try:
                    chunk = os.read(pipe.fileno(), 8192)
                except BlockingIOError:
                    break
                if not chunk:
                    break
                truncated = _append_stderr_tail(buffer, chunk) or truncated
            process.wait()
            return bytes(buffer), truncated
    finally:
        selector.close()
        try:
            pipe.close()
        except OSError:
            pass


def _stderr_tail(payload: bytes, *, truncated: bool = False) -> str:
    """Decode and sanitize a bounded stderr tail for UI presentation."""

    text = payload.decode("utf-8", errors="replace")
    text = _ANSI_ESCAPE.sub("", text)
    cleaned = "".join(
        char
        for char in text
        if char in "\n\r\t" or unicodedata.category(char) != "Cc"
    ).strip()
    if truncated:
        cleaned = "[earlier output truncated]\n" + cleaned
    return cleaned


def _format_process_failure(
    title: str,
    exit_code: int,
    stderr_text: str,
) -> str:
    message = f"{title} exited with code {exit_code}."
    if stderr_text:
        message += f"\n\nDetails:\n{stderr_text}"
    return message


class DesktopProcessManager(QtCore.QObject):
    """Start desktop-entry processes and report asynchronous failures."""

    launch_started = QtCore.Signal(str, str)
    launch_delegated = QtCore.Signal(str, str)
    launch_finished = QtCore.Signal(str, str, int)
    launch_failed = QtCore.Signal(str, str, str, bool)

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._active: dict[int, _RunningLaunch] = {}
        self._lock = threading.Lock()
        self._shutting_down = False

    def active_count(self) -> int:
        with self._lock:
            return len(self._active)

    def launch(
        self,
        filepath: str | Path,
        *,
        launch_input: DesktopLaunchInput | None = None,
        working_directory: str | None = None,
    ) -> int:
        """Prepare and start one or more processes, returning their count."""

        prepared = prepare_desktop_launch(
            filepath,
            launch_input=launch_input,
            working_directory=working_directory,
        )
        return self.launch_prepared(prepared)

    def launch_prepared(self, prepared: PreparedDesktopLaunch) -> int:
        """Start a previously validated launch without preparing it again."""

        launched_count = 0
        for command in prepared.commands:
            self._start_command(prepared, command)
            launched_count += 1
        return launched_count

    def _start_command(
        self,
        prepared: PreparedDesktopLaunch,
        command: tuple[str, ...],
    ) -> None:
        # Import lazily to keep the preparation helpers free of a circular import.
        from app.services.system_utils import external_process_environment

        try:
            process = subprocess.Popen(
                list(command),
                cwd=str(prepared.working_directory),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                shell=False,
                env=external_process_environment(command[0]),
                start_new_session=True,
            )
        except Exception:
            raise

        state = _RunningLaunch(
            process=process,
            source_path=str(prepared.metadata.source_path),
            title=prepared.metadata.name,
            mode=prepared.mode,
            started_at=time.monotonic(),
        )
        with self._lock:
            self._active[process.pid] = state

        if prepared.mode == "gio":
            self.launch_delegated.emit(state.source_path, state.title)
        else:
            self.launch_started.emit(state.source_path, state.title)

        monitor = threading.Thread(
            target=self._monitor_process,
            args=(state,),
            name=f"toolbox-desktop-{process.pid}",
            daemon=True,
        )
        monitor.start()

    def _monitor_process(self, state: _RunningLaunch) -> None:
        try:
            stderr_payload, stderr_truncated = _capture_stderr(state.process)
            exit_code = state.process.returncode
            if exit_code is None:  # pragma: no cover - defensive OS boundary
                exit_code = state.process.wait()
            elapsed = time.monotonic() - state.started_at
            stderr_text = _stderr_tail(
                stderr_payload,
                truncated=stderr_truncated,
            )
        except Exception as exc:  # pragma: no cover - defensive OS boundary
            exit_code = -1
            elapsed = 0.0
            stderr_text = str(exc)
        finally:
            with self._lock:
                self._active.pop(state.process.pid, None)

        if self._shutting_down:
            return
        if exit_code != 0:
            self.launch_failed.emit(
                state.source_path,
                state.title,
                _format_process_failure(state.title, exit_code, stderr_text),
                elapsed <= FAST_FAILURE_SECONDS,
            )
            return
        if state.mode == "gio":
            # GIO completion confirms delegation only, not target completion.
            return
        self.launch_finished.emit(state.source_path, state.title, exit_code)

    def shutdown(self) -> None:
        """Stop emitting UI updates without terminating launched applications."""

        self._shutting_down = True
