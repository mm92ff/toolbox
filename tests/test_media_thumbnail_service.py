from __future__ import annotations

import os
import threading
import time
from pathlib import Path

from PySide6 import QtCore

from app import constants
from app.services import media_thumbnails
from app.services.media_thumbnails import (
    MEDIA_KIND_IMAGE,
    MEDIA_KIND_VIDEO,
    MediaThumbnailService,
)
from app.services.thumbnail_cache import prune_thumbnail_cache, thumbnail_bucket_size


def _wait_for_results(
    service: MediaThumbnailService,
    expected: int,
    timeout_ms: int = 2000,
) -> list[tuple[str, str, int, str, str]]:
    results: list[tuple[str, str, int, str, str]] = []
    loop = QtCore.QEventLoop()

    def collect(path: str, kind: str, bucket: int, mode: str, output: str) -> None:
        results.append((path, kind, bucket, mode, output))
        if len(results) >= expected:
            loop.quit()

    service.result_ready.connect(collect)
    QtCore.QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    service.result_ready.disconnect(collect)
    return results


def test_slow_thumbnail_generation_runs_outside_gui_thread(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "photo.png"
    source.write_bytes(b"source")
    cache_dir = tmp_path / "cache"
    worker_threads: list[int] = []

    def slow_prepare(
        _path: str, icon_size: int, _mode: str, target_cache: Path
    ) -> Path:
        worker_threads.append(threading.get_ident())
        time.sleep(0.08)
        output = target_cache / f"{icon_size}.png"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"thumbnail")
        return output

    monkeypatch.setattr(media_thumbnails, "prepare_thumbnail_cache", slow_prepare)
    service = MediaThumbnailService(image_workers=1)
    started = time.monotonic()
    service.request(
        str(source),
        MEDIA_KIND_IMAGE,
        72,
        constants.IMAGE_PREVIEW_MODE_FIT,
        cache_dir,
    )
    request_duration = time.monotonic() - started
    results = _wait_for_results(service, 1)
    service.shutdown()

    assert request_duration < 0.04
    assert len(results) == 1
    assert worker_threads and worker_threads[0] != threading.get_ident()


def test_requests_for_one_video_are_serialized(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "clip.mp4"
    source.write_bytes(b"video")
    cache_dir = tmp_path / "cache"
    lock = threading.Lock()
    active = 0
    max_active = 0

    def slow_prepare(
        _path: str,
        icon_size: int,
        _mode: str,
        target_cache: Path,
        **_kwargs: object,
    ) -> Path:
        nonlocal active, max_active
        with lock:
            active += 1
            max_active = max(max_active, active)
        time.sleep(0.04)
        output = target_cache / f"{icon_size}.png"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"thumbnail")
        with lock:
            active -= 1
        return output

    monkeypatch.setattr(media_thumbnails, "prepare_video_thumbnail_cache", slow_prepare)
    service = MediaThumbnailService(video_workers=2)
    service.request(
        str(source), MEDIA_KIND_VIDEO, 72, "fit", cache_dir
    )
    service.request(
        str(source), MEDIA_KIND_VIDEO, 128, "fit", cache_dir
    )
    results = _wait_for_results(service, 2)
    service.shutdown()

    assert len(results) == 2
    assert {result[2] for result in results} == {
        thumbnail_bucket_size(72),
        thumbnail_bucket_size(128),
    }
    assert max_active == 1


def test_cache_pruning_removes_oldest_files_first(tmp_path: Path) -> None:
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    oldest = cache_dir / "oldest.png"
    middle = cache_dir / "middle.png"
    newest = cache_dir / "newest.png"
    for path in (oldest, middle, newest):
        path.write_bytes(b"x" * 60)
    now = time.time()
    os.utime(oldest, (now - 30, now - 30))
    os.utime(middle, (now - 20, now - 20))
    os.utime(newest, (now - 10, now - 10))

    removed, remaining_bytes = prune_thumbnail_cache(cache_dir, 100)

    assert removed == 2
    assert remaining_bytes == 60
    assert not oldest.exists()
    assert not middle.exists()
    assert newest.exists()
