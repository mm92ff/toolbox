from __future__ import annotations

import os
from pathlib import Path
import shutil
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets
import pytest

from app.services.desktop_entries import DesktopEntryError, DesktopLaunchInput
from app.services.desktop_entry_launch import (
    MAX_CAPTURED_STDERR_BYTES,
    DesktopProcessManager,
    _append_stderr_tail,
    _stderr_tail,
    prepare_desktop_launch,
)


def _write_executable(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)
    return path


def _write_desktop(
    path: Path,
    executable: Path | str,
    *,
    field_code: str = "",
    extra: str = "",
) -> Path:
    path.write_text(
        (
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=Launch Test\n"
            f"Exec={executable}{(' ' + field_code) if field_code else ''}\n"
            "Terminal=false\n"
            f"{extra}"
        ),
        encoding="utf-8",
    )
    path.chmod(0o755)
    return path


def _wait_until(predicate: object, timeout: float = 3.0) -> bool:
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if callable(predicate) and predicate():
            return True
        time.sleep(0.01)
    app.processEvents()
    return bool(callable(predicate) and predicate())


def test_prepare_direct_launch_resolves_executable_and_working_directory(
    tmp_path: Path,
) -> None:
    executable = _write_executable(tmp_path / "helper", "#!/bin/sh\nexit 0\n")
    desktop = _write_desktop(
        tmp_path / "Test.desktop",
        executable,
        extra=f"Path={tmp_path}\n",
    )

    prepared = prepare_desktop_launch(desktop)

    assert prepared.mode == "direct"
    assert prepared.commands == ((str(executable),),)
    assert prepared.working_directory == tmp_path


def test_explicit_working_directory_overrides_desktop_path(tmp_path: Path) -> None:
    executable = _write_executable(tmp_path / "helper", "#!/bin/sh\nexit 0\n")
    declared = tmp_path / "declared"
    override = tmp_path / "override"
    declared.mkdir()
    override.mkdir()
    desktop = _write_desktop(
        tmp_path / "Test.desktop",
        executable,
        extra=f"Path={declared}\n",
    )

    prepared = prepare_desktop_launch(
        desktop,
        working_directory=str(override),
    )

    assert prepared.working_directory == override


def test_prepare_rejects_missing_try_exec(tmp_path: Path) -> None:
    desktop = _write_desktop(
        tmp_path / "Test.desktop",
        "/usr/bin/true",
        extra="TryExec=definitely-missing-toolbox-command\n",
    )

    with pytest.raises(DesktopEntryError, match="not found"):
        prepare_desktop_launch(desktop)


def test_prepare_rejects_missing_working_directory(tmp_path: Path) -> None:
    desktop = _write_desktop(
        tmp_path / "Test.desktop",
        "/usr/bin/true",
        extra=f"Path={tmp_path / 'missing'}\n",
    )

    with pytest.raises(DesktopEntryError, match="working directory not found"):
        prepare_desktop_launch(desktop)


def test_prepare_terminal_entry_uses_gio_fallback(tmp_path: Path) -> None:
    if shutil.which("gio") is None:
        pytest.skip("gio is unavailable")
    desktop = _write_desktop(
        tmp_path / "Terminal.desktop",
        "/usr/bin/true",
        extra="Terminal=true\n",
    )

    prepared = prepare_desktop_launch(desktop)

    assert prepared.mode == "gio"
    assert prepared.commands[0][1:3] == ("launch", str(desktop.resolve()))


def test_prepare_terminal_entry_validates_exec_before_gio_fallback(
    tmp_path: Path,
) -> None:
    desktop = _write_desktop(
        tmp_path / "Terminal.desktop",
        "/usr/bin/true",
        field_code="%x",
        extra="Terminal=true\n",
    )

    with pytest.raises(DesktopEntryError, match="unknown field code"):
        prepare_desktop_launch(desktop)


def test_prepare_terminal_entry_rejects_drop_without_file_field_code(
    tmp_path: Path,
) -> None:
    desktop = _write_desktop(
        tmp_path / "Terminal.desktop",
        "/usr/bin/true",
        extra="Terminal=true\n",
    )

    with pytest.raises(DesktopEntryError, match="does not accept"):
        prepare_desktop_launch(
            desktop,
            launch_input=DesktopLaunchInput.from_local_paths(
                (tmp_path / "input.txt",)
            ),
        )


def test_prepare_link_entry_uses_system_opener(tmp_path: Path) -> None:
    if shutil.which("xdg-open") is None and shutil.which("gio") is None:
        pytest.skip("desktop opener is unavailable")
    desktop = tmp_path / "Link.desktop"
    desktop.write_text(
        (
            "[Desktop Entry]\n"
            "Type=Link\n"
            "Name=Example\n"
            "URL=https://example.com/\n"
        ),
        encoding="utf-8",
    )

    prepared = prepare_desktop_launch(desktop)

    assert prepared.mode == "link"
    assert "https://example.com/" in prepared.commands[0]


def test_process_manager_reports_fast_failure_with_stderr(tmp_path: Path) -> None:
    executable = _write_executable(
        tmp_path / "fails",
        "#!/bin/sh\nprintf 'controlled failure\\n' >&2\nexit 7\n",
    )
    desktop = _write_desktop(tmp_path / "Failure.desktop", executable)
    manager = DesktopProcessManager()
    failures: list[tuple[str, str, str, bool]] = []
    manager.launch_failed.connect(
        lambda path, title, message, fast: failures.append(
            (path, title, message, fast)
        )
    )

    assert manager.launch(desktop) == 1
    assert _wait_until(lambda: bool(failures))

    _path, title, message, fast = failures[0]
    assert title == "Launch Test"
    assert "code 7" in message
    assert "controlled failure" in message
    assert fast is True
    assert _wait_until(lambda: manager.active_count() == 0)


def test_process_manager_runs_percent_f_drop_without_shell(tmp_path: Path) -> None:
    output = tmp_path / "arguments.txt"
    executable = _write_executable(
        tmp_path / "capture",
        f"#!/bin/sh\nprintf '%s\\n' \"$@\" > '{output}'\n",
    )
    desktop = _write_desktop(
        tmp_path / "Capture.desktop",
        executable,
        field_code="%F",
    )
    first = tmp_path / "one file.txt"
    second = tmp_path / "literal;$(false).txt"
    manager = DesktopProcessManager()

    manager.launch(
        desktop,
        launch_input=DesktopLaunchInput.from_local_paths((first, second)),
    )

    assert _wait_until(output.exists)
    assert output.read_text(encoding="utf-8").splitlines() == [
        str(first),
        str(second),
    ]


def test_process_manager_success_signal_is_emitted(tmp_path: Path) -> None:
    executable = _write_executable(tmp_path / "success", "#!/bin/sh\nexit 0\n")
    desktop = _write_desktop(tmp_path / "Success.desktop", executable)
    manager = DesktopProcessManager()
    started: list[str] = []
    finished: list[int] = []
    manager.launch_started.connect(lambda _path, title: started.append(title))
    manager.launch_finished.connect(
        lambda _path, _title, code: finished.append(code)
    )

    manager.launch(desktop)

    assert started == ["Launch Test"]
    assert _wait_until(lambda: finished == [0])


def test_process_manager_launch_is_non_blocking_for_long_running_process(
    tmp_path: Path,
) -> None:
    executable = _write_executable(
        tmp_path / "long-running",
        "#!/bin/sh\nsleep 0.4\nexit 0\n",
    )
    desktop = _write_desktop(tmp_path / "Long.desktop", executable)
    manager = DesktopProcessManager()

    started_at = time.monotonic()
    manager.launch(desktop)
    elapsed = time.monotonic() - started_at

    assert elapsed < 0.2
    assert manager.active_count() == 1
    assert _wait_until(lambda: manager.active_count() == 0)


def test_process_manager_tracks_concurrent_outputs_separately(tmp_path: Path) -> None:
    first_executable = _write_executable(
        tmp_path / "first",
        "#!/bin/sh\nprintf 'first-only\\n' >&2\nexit 3\n",
    )
    second_executable = _write_executable(
        tmp_path / "second",
        "#!/bin/sh\nprintf 'second-only\\n' >&2\nexit 4\n",
    )
    first_desktop = _write_desktop(tmp_path / "First.desktop", first_executable)
    second_desktop = _write_desktop(tmp_path / "Second.desktop", second_executable)
    manager = DesktopProcessManager()
    failures: dict[str, str] = {}
    manager.launch_failed.connect(
        lambda path, _title, message, _fast: failures.__setitem__(
            Path(path).name,
            message,
        )
    )

    manager.launch(first_desktop)
    manager.launch(second_desktop)

    assert _wait_until(lambda: len(failures) == 2)
    assert "first-only" in failures["First.desktop"]
    assert "second-only" not in failures["First.desktop"]
    assert "second-only" in failures["Second.desktop"]
    assert "first-only" not in failures["Second.desktop"]


def test_process_manager_bounds_large_stderr_output(tmp_path: Path) -> None:
    executable = _write_executable(
        tmp_path / "large-error",
        (
            "#!/usr/bin/python3\n"
            "import sys\n"
            "sys.stderr.write('x' * 80000)\n"
            "raise SystemExit(9)\n"
        ),
    )
    desktop = _write_desktop(tmp_path / "Large.desktop", executable)
    manager = DesktopProcessManager()
    failures: list[str] = []
    manager.launch_failed.connect(
        lambda _path, _title, message, _fast: failures.append(message)
    )

    manager.launch(desktop)

    assert _wait_until(lambda: bool(failures))
    assert "[earlier output truncated]" in failures[0]
    assert len(failures[0].encode("utf-8")) < 66_000


def test_stderr_ring_buffer_never_exceeds_hard_limit() -> None:
    buffer = bytearray()
    truncated = False

    for _index in range(40):
        truncated = _append_stderr_tail(buffer, b"x" * 4096) or truncated

    assert truncated is True
    assert len(buffer) == MAX_CAPTURED_STDERR_BYTES


def test_stderr_details_remove_ansi_and_control_characters() -> None:
    details = _stderr_tail(
        b"\x1b[31mred\x1b[0m\x00\x01\x7f"
        + "\u0080".encode("utf-8")
        + b"safe\n",
    )

    assert details == "redsafe"
