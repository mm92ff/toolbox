from __future__ import annotations

import os
import threading
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets

from app.services.folder_count import FolderCountService


def _application() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _wait_for_results(
    service: FolderCountService,
    expected: int,
    timeout_ms: int = 3000,
    trigger=None,
) -> list[tuple[str, int, str]]:
    app = _application()
    results: list[tuple[str, int, str]] = []
    loop = QtCore.QEventLoop()

    def collect(path: str, count: int, error: str) -> None:
        results.append((path, count, error))
        if len(results) >= expected:
            loop.quit()

    service.result_ready.connect(collect)
    timeout = QtCore.QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(loop.quit)
    timeout.start(timeout_ms)
    if trigger is not None:
        trigger()
    loop.exec()
    app.processEvents()
    service.result_ready.disconnect(collect)
    return results


def test_folder_count_is_bounded_and_counts_only_visible_direct_children(tmp_path) -> None:
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "visible.txt").write_text("ok", encoding="utf-8")
    (folder / ".hidden").write_text("hidden", encoding="utf-8")
    (folder / "subfolder").mkdir()
    service = FolderCountService(max_workers=2)

    service.request(str(folder))
    results = _wait_for_results(service, 1)

    assert service.max_workers == 2
    assert results == [(str(folder.resolve()), 2, "")]
    service.shutdown()


def test_folder_count_uses_cache_and_reports_missing_folder(tmp_path) -> None:
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "one").write_text("1", encoding="utf-8")
    service = FolderCountService()

    service.request(str(folder))
    assert _wait_for_results(service, 1)[0][1:] == (1, "")
    service.request(str(folder))
    assert _wait_for_results(service, 1)[0][1:] == (1, "")
    (folder / "two").write_text("2", encoding="utf-8")
    service.request(str(folder))
    assert _wait_for_results(service, 1)[0][1:] == (2, "")

    service.request(str(tmp_path / "missing"))
    missing = _wait_for_results(service, 1)
    assert missing and missing[0][1] == 0
    assert missing[0][2]
    service.shutdown()


def test_folder_count_shutdown_rejects_new_requests(tmp_path) -> None:
    service = FolderCountService()
    service.shutdown()

    service.request(str(tmp_path))

    assert service._pending == set()
    assert service._tasks == {}


def test_folder_count_reports_permission_error(tmp_path) -> None:
    folder = tmp_path / "private"
    folder.mkdir()
    service = FolderCountService()

    with patch(
        "app.services.folder_count.os.scandir",
        side_effect=PermissionError("denied"),
    ):
        results = _wait_for_results(
            service,
            1,
            trigger=lambda: service.request(str(folder)),
        )

    assert results == [(str(folder.resolve()), 0, "Keine Leseberechtigung")]
    service.shutdown()


def test_folder_count_rejects_symlink_loop_without_resolving_it(tmp_path) -> None:
    loop = tmp_path / "loop"
    loop.symlink_to(loop)
    service = FolderCountService()

    results = _wait_for_results(
        service,
        1,
        trigger=lambda: service.request(str(loop)),
    )

    assert results
    assert results[0][0] == str(loop.absolute())
    assert results[0][1] == 0
    assert results[0][2]
    service.shutdown()


def test_many_requests_never_exceed_worker_limit(tmp_path) -> None:
    folders = []
    for index in range(20):
        folder = tmp_path / str(index)
        folder.mkdir()
        folders.append(folder)
    active = 0
    maximum_active = 0
    lock = threading.Lock()
    two_started = threading.Event()
    release = threading.Event()

    class BlockingScan:
        def __enter__(self):
            nonlocal active, maximum_active
            with lock:
                active += 1
                maximum_active = max(maximum_active, active)
                if active == 2:
                    two_started.set()
            release.wait(3)
            return iter(())

        def __exit__(self, *_args: object) -> None:
            nonlocal active
            with lock:
                active -= 1

    service = FolderCountService(max_workers=2)
    with patch("app.services.folder_count.os.scandir", side_effect=lambda _path: BlockingScan()):
        for folder in folders:
            service.request(str(folder))
        assert two_started.wait(2)
        assert maximum_active == 2
        assert len(
            _wait_for_results(service, len(folders), trigger=release.set)
        ) == len(folders)
    service.shutdown()


def test_repeated_requests_for_pending_path_start_only_one_job(tmp_path) -> None:
    folder = tmp_path / "folder"
    folder.mkdir()
    started = threading.Event()
    release = threading.Event()

    class BlockingScan:
        def __enter__(self):
            started.set()
            release.wait(3)
            return iter(())

        def __exit__(self, *_args: object) -> None:
            return None

    service = FolderCountService()
    with patch(
        "app.services.folder_count.os.scandir",
        side_effect=lambda _path: BlockingScan(),
    ) as scandir:
        for _ in range(10):
            service.request(str(folder))
        assert started.wait(2)
        assert len(_wait_for_results(service, 1, trigger=release.set)) == 1
        assert scandir.call_count == 1
    service.shutdown()
