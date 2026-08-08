from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest
from PySide6 import QtCore, QtGui

from app.services.appimage_icons import (
    AppImageIconService,
    cached_appimage_icon_path,
    extract_appimage_icon_static,
    find_squashfs_offset,
)


def _build_appimage_fixture(tmp_path: Path) -> tuple[Path, Path, int]:
    mksquashfs = shutil.which("mksquashfs")
    if mksquashfs is None or not Path("/usr/bin/unsquashfs").is_file():
        pytest.skip("squashfs-tools are unavailable")

    root = tmp_path / "root"
    root.mkdir()
    icon_path = root / "fixture.png"
    image = QtGui.QImage(48, 48, QtGui.QImage.Format.Format_ARGB32)
    image.fill(QtGui.QColor("#2678d4"))
    assert image.save(str(icon_path), "PNG")
    (root / ".DirIcon").symlink_to(icon_path.name)

    squashfs = tmp_path / "payload.squashfs"
    completed = subprocess.run(
        [
            mksquashfs,
            str(root),
            str(squashfs),
            "-noappend",
            "-processors",
            "1",
            "-quiet",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr

    marker = tmp_path / "target-was-executed"
    prefix = (
        f"#!/bin/sh\ntouch '{marker}'\nexit 0\n# invalid hsqs marker\n".encode()
    )
    appimage = tmp_path / "Static Fixture.AppImage"
    appimage.write_bytes(prefix + squashfs.read_bytes())
    appimage.chmod(0o755)
    return appimage, marker, len(prefix)


def _wait_for_icon(service: AppImageIconService, path: Path) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    loop = QtCore.QEventLoop()

    def collect(result_path: str, icon_path: str) -> None:
        results.append((result_path, icon_path))
        loop.quit()

    service.result_ready.connect(collect)
    timeout = QtCore.QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(loop.quit)
    timeout.start(5000)
    service.request(path)
    loop.exec()
    service.result_ready.disconnect(collect)
    return results


def test_static_extraction_finds_valid_superblock_after_false_magic(tmp_path: Path) -> None:
    appimage, marker, expected_offset = _build_appimage_fixture(tmp_path)

    assert find_squashfs_offset(appimage) == expected_offset
    assert not marker.exists()


def test_background_service_extracts_diricon_without_executing_target(
    tmp_path: Path,
) -> None:
    appimage, marker, _offset = _build_appimage_fixture(tmp_path)
    cache_dir = tmp_path / "cache"
    service = AppImageIconService(cache_dir=cache_dir)

    results = _wait_for_icon(service, appimage)

    assert len(results) == 1
    assert results[0][0] == str(appimage.absolute())
    cached_icon = Path(results[0][1])
    assert cached_icon.parent == cache_dir
    assert cached_icon.is_file()
    image = QtGui.QImage(str(cached_icon))
    assert not image.isNull()
    assert image.pixelColor(image.width() // 2, image.height() // 2).name() == "#2678d4"
    assert not marker.exists()
    assert service.max_workers == 1
    service.shutdown()


def test_static_cache_invalidates_when_appimage_changes(tmp_path: Path) -> None:
    appimage, marker, _offset = _build_appimage_fixture(tmp_path)
    cache_dir = tmp_path / "cache"
    first = extract_appimage_icon_static(appimage, cache_dir=cache_dir)

    assert first
    assert cached_appimage_icon_path(
        appimage,
        cache_dir=cache_dir,
        include_legacy=False,
    ) == first
    with appimage.open("ab") as stream:
        stream.write(b"changed")
    os.utime(appimage, None)

    assert cached_appimage_icon_path(
        appimage,
        cache_dir=cache_dir,
        include_legacy=False,
    ) == ""
    assert not marker.exists()


def test_invalid_appimage_never_starts_a_parser_or_target(tmp_path: Path, monkeypatch) -> None:
    marker = tmp_path / "executed"
    target = tmp_path / "Invalid.AppImage"
    target.write_text(f"#!/bin/sh\ntouch '{marker}'\n", encoding="utf-8")
    target.chmod(0o755)

    def unexpected_process(*_args, **_kwargs):
        raise AssertionError("no child process is needed without a SquashFS payload")

    monkeypatch.setattr("app.services.appimage_icons.subprocess.Popen", unexpected_process)

    assert extract_appimage_icon_static(target, cache_dir=tmp_path / "cache") == ""
    assert not marker.exists()
