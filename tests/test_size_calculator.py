from __future__ import annotations

import threading
import socket
import tempfile
from pathlib import Path
from unittest.mock import patch

from PySide6 import QtCore

from app.services.size_calculator import (
    TabSizeCalculationService,
    calculate_paths_size,
    format_size,
)


def test_format_size_uses_binary_units() -> None:
    assert format_size(1) == "1 B"
    assert format_size(1024) == "1.0 KiB"
    assert format_size(1024 * 1024) == "1.0 MiB"
    assert format_size(1024 * 1024 * 1024) == "1.0 GiB"
    assert format_size(1024, approximate=True) == "≥ 1.0 KiB (geschätzt)"


def test_size_calculation_deduplicates_files(tmp_path: Path) -> None:
    source = tmp_path / "payload.bin"
    source.write_bytes(b"12345678")

    assert calculate_paths_size([str(source), str(source)]) == "8 B"


def test_size_calculation_deduplicates_nested_paths(tmp_path: Path) -> None:
    folder = tmp_path / "folder"
    folder.mkdir()
    child = folder / "payload.bin"
    child.write_bytes(b"12345678")

    assert calculate_paths_size([str(child), str(folder)]) == "8 B"


def test_cancelled_size_calculation_returns_none(tmp_path: Path) -> None:
    cancelled = threading.Event()
    cancelled.set()

    assert calculate_paths_size([str(tmp_path)], cancelled) is None


def test_missing_and_non_file_paths_are_reported_unavailable(tmp_path: Path) -> None:
    assert calculate_paths_size([str(tmp_path / "missing")]) == "Nicht verfügbar"


def test_empty_path_snapshot_is_exact_zero() -> None:
    assert calculate_paths_size([]) == "0 B"


def test_symlink_and_socket_are_not_followed_or_counted(tmp_path: Path) -> None:
    target = tmp_path / "target.bin"
    target.write_bytes(b"payload")
    symlink = tmp_path / "link.bin"
    symlink.symlink_to(target)
    assert calculate_paths_size([str(symlink)]) == "Nicht verfügbar"

    with tempfile.TemporaryDirectory(prefix="toolbox-socket-", dir="/tmp") as socket_dir:
        socket_path = Path(socket_dir) / "service.sock"
        unix_socket = socket.socket(socket.AF_UNIX)
        try:
            unix_socket.bind(str(socket_path))
            assert calculate_paths_size([str(socket_path)]) == "Nicht verfügbar"
        finally:
            unix_socket.close()


def test_unreadable_directory_is_reported_as_estimate(tmp_path: Path) -> None:
    with patch("app.services.size_calculator.os.scandir", side_effect=PermissionError):
        assert calculate_paths_size([str(tmp_path)]) == "≥ 0 B (geschätzt)"


def test_timeout_is_reported_as_estimate(tmp_path: Path) -> None:
    with patch("app.services.size_calculator.time.monotonic", side_effect=[0.0, 2.0]):
        assert calculate_paths_size([str(tmp_path)], timeout_seconds=1.0) == (
            "≥ 0 B (geschätzt)"
        )


def test_size_service_runs_off_gui_thread_and_limits_workers(qapp) -> None:
    service = TabSizeCalculationService()
    release = threading.Event()
    timer_fired = False
    results: list[tuple[str, str]] = []
    loop = QtCore.QEventLoop()

    def calculate(_paths, cancelled):
        while not release.wait(0.01):
            if cancelled.is_set():
                return None
        return "1 B"

    def on_timer() -> None:
        nonlocal timer_fired
        timer_fired = True
        release.set()

    service.result_ready.connect(lambda tab, result: (results.append((tab, result)), loop.quit()))
    with patch("app.services.size_calculator.calculate_paths_size", side_effect=calculate):
        service.request("tab", ("/tmp/file",))
        QtCore.QTimer.singleShot(20, on_timer)
        QtCore.QTimer.singleShot(2000, loop.quit)
        loop.exec()

    assert timer_fired is True
    assert service.max_workers == 1
    assert results == [("tab", "1 B")]
    service.shutdown()


def test_stale_size_result_is_discarded(qapp) -> None:
    del qapp
    service = TabSizeCalculationService()
    old_started = threading.Event()
    results: list[tuple[str, str]] = []
    loop = QtCore.QEventLoop()

    def calculate(paths, cancelled):
        if paths == ("old",):
            old_started.set()
            while not cancelled.wait(0.01):
                pass
            return "stale"
        return "fresh"

    service.result_ready.connect(lambda tab, result: (results.append((tab, result)), loop.quit()))
    with patch("app.services.size_calculator.calculate_paths_size", side_effect=calculate):
        service.request("old-tab", ("old",))
        assert old_started.wait(1)
        service.request("new-tab", ("new",))
        QtCore.QTimer.singleShot(2000, loop.quit)
        loop.exec()

    assert results == [("new-tab", "fresh")]
    service.shutdown()
