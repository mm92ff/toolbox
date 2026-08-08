from __future__ import annotations

import hashlib
import io
import tarfile
import threading
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services import ffmpeg_downloader


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _hash(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _archive(path: Path, ffmpeg: bytes, ffprobe: bytes) -> Path:
    with tarfile.open(path, "w:xz") as tar:
        for name, payload in (("bundle/ffmpeg", ffmpeg), ("bundle/ffprobe", ffprobe)):
            member = tarfile.TarInfo(name)
            member.size = len(payload)
            member.mode = 0o755
            tar.addfile(member, io.BytesIO(payload))
    return path


def test_verified_linux_install_uses_user_data_directory(tmp_path: Path) -> None:
    ffmpeg = b"verified-ffmpeg"
    ffprobe = b"verified-ffprobe"
    archive = _archive(tmp_path / "ffmpeg.tar.xz", ffmpeg, ffprobe)
    hashes = {"ffmpeg": _hash(ffmpeg), "ffprobe": _hash(ffprobe)}

    with (
        patch("app.services.ffmpeg_downloader.platform.system", return_value="Linux"),
        patch("app.services.ffmpeg_downloader.platform.machine", return_value="x86_64"),
        patch.object(ffmpeg_downloader, "EXPECTED_BINARY_SHA256", hashes),
        patch.object(ffmpeg_downloader, "EXPECTED_ARCHIVE_SHA256", _hash(archive.read_bytes())),
    ):
        result = ffmpeg_downloader.download_and_extract_ffmpeg(
            archive_source=archive,
            data_root=tmp_path / "data",
        )

    assert result == tmp_path / "data" / ffmpeg_downloader.FFMPEG_VERSION / "ffmpeg"
    assert result.read_bytes() == ffmpeg
    assert result.stat().st_mode & 0o111
    assert result.with_name("ffprobe").read_bytes() == ffprobe


def test_hash_mismatch_is_rejected_without_installing(tmp_path: Path) -> None:
    archive = _archive(tmp_path / "ffmpeg.tar.xz", b"wrong", b"also-wrong")
    hashes = {"ffmpeg": "0" * 64, "ffprobe": "1" * 64}

    with (
        patch("app.services.ffmpeg_downloader.platform.system", return_value="Linux"),
        patch("app.services.ffmpeg_downloader.platform.machine", return_value="x86_64"),
        patch.object(ffmpeg_downloader, "EXPECTED_BINARY_SHA256", hashes),
        patch.object(ffmpeg_downloader, "EXPECTED_ARCHIVE_SHA256", _hash(archive.read_bytes())),
        pytest.raises(RuntimeError, match="SHA-256 mismatch"),
    ):
        ffmpeg_downloader.download_and_extract_ffmpeg(
            archive_source=archive,
            data_root=tmp_path / "data",
        )

    assert not (tmp_path / "data" / ffmpeg_downloader.FFMPEG_VERSION).exists()


def test_symlink_member_for_binary_is_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.tar.xz"
    with tarfile.open(archive, "w:xz") as tar:
        member = tarfile.TarInfo("bundle/ffmpeg")
        member.type = tarfile.SYMTYPE
        member.linkname = "/tmp/payload"
        tar.addfile(member)

    with (
        patch("app.services.ffmpeg_downloader.platform.system", return_value="Linux"),
        patch("app.services.ffmpeg_downloader.platform.machine", return_value="x86_64"),
        patch.object(ffmpeg_downloader, "EXPECTED_ARCHIVE_SHA256", _hash(archive.read_bytes())),
        pytest.raises(RuntimeError, match="Unsafe archive member"),
    ):
        ffmpeg_downloader.download_and_extract_ffmpeg(
            archive_source=archive,
            data_root=tmp_path / "data",
        )


def test_path_traversal_member_is_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe-path.tar.xz"
    with tarfile.open(archive, "w:xz") as tar:
        member = tarfile.TarInfo("../ffmpeg")
        member.size = 1
        tar.addfile(member, io.BytesIO(b"x"))

    with (
        patch("app.services.ffmpeg_downloader.platform.system", return_value="Linux"),
        patch("app.services.ffmpeg_downloader.platform.machine", return_value="x86_64"),
        patch.object(ffmpeg_downloader, "EXPECTED_ARCHIVE_SHA256", _hash(archive.read_bytes())),
        pytest.raises(RuntimeError, match="Unsafe archive path"),
    ):
        ffmpeg_downloader.download_and_extract_ffmpeg(
            archive_source=archive,
            data_root=tmp_path / "data",
        )


def test_archive_hash_mismatch_is_rejected_before_extraction(tmp_path: Path) -> None:
    archive = _archive(tmp_path / "ffmpeg.tar.xz", b"ffmpeg", b"ffprobe")

    with (
        patch("app.services.ffmpeg_downloader.platform.system", return_value="Linux"),
        patch("app.services.ffmpeg_downloader.platform.machine", return_value="x86_64"),
        patch.object(ffmpeg_downloader, "EXPECTED_ARCHIVE_SHA256", "0" * 64),
        pytest.raises(RuntimeError, match="FFmpeg archive"),
    ):
        ffmpeg_downloader.download_and_extract_ffmpeg(
            archive_source=archive,
            data_root=tmp_path / "data",
        )


def test_runtime_archive_hash_matches_versioned_manifest() -> None:
    manifest = (
        PROJECT_ROOT / "packaging" / "linux" / "ffmpeg-archive-x86_64.sha256"
    ).read_text(encoding="utf-8")

    assert manifest.split()[0] == ffmpeg_downloader.EXPECTED_ARCHIVE_SHA256


def test_absolute_binary_member_is_rejected(tmp_path: Path) -> None:
    archive = tmp_path / "absolute.tar.xz"
    with tarfile.open(archive, "w:xz") as tar:
        member = tarfile.TarInfo("/bundle/ffmpeg")
        member.size = 1
        tar.addfile(member, io.BytesIO(b"x"))

    with (
        patch("app.services.ffmpeg_downloader.platform.system", return_value="Linux"),
        patch("app.services.ffmpeg_downloader.platform.machine", return_value="x86_64"),
        patch.object(ffmpeg_downloader, "EXPECTED_ARCHIVE_SHA256", _hash(archive.read_bytes())),
        pytest.raises(RuntimeError, match="Unsafe archive path"),
    ):
        ffmpeg_downloader.download_and_extract_ffmpeg(
            archive_source=archive,
            data_root=tmp_path / "data",
        )


@pytest.mark.parametrize("machine", ["aarch64", "riscv64", "unknown"])
def test_unsupported_architecture_is_rejected(tmp_path: Path, machine: str) -> None:
    with (
        patch("app.services.ffmpeg_downloader.platform.system", return_value="Linux"),
        patch("app.services.ffmpeg_downloader.platform.machine", return_value=machine),
        pytest.raises(RuntimeError, match="Linux x86_64 only"),
    ):
        ffmpeg_downloader.download_and_extract_ffmpeg(data_root=tmp_path)


def test_cancelled_install_leaves_no_partial_version_directory(tmp_path: Path) -> None:
    archive = _archive(tmp_path / "ffmpeg.tar.xz", b"ffmpeg", b"ffprobe")
    cancelled = threading.Event()
    cancelled.set()

    with (
        patch("app.services.ffmpeg_downloader.platform.system", return_value="Linux"),
        patch("app.services.ffmpeg_downloader.platform.machine", return_value="x86_64"),
        pytest.raises(RuntimeError, match="cancelled"),
    ):
        ffmpeg_downloader.download_and_extract_ffmpeg(
            archive_source=archive,
            data_root=tmp_path / "data",
            cancelled=cancelled,
        )

    assert not (tmp_path / "data" / ffmpeg_downloader.FFMPEG_VERSION).exists()


def test_http_error_is_propagated_without_partial_install(tmp_path: Path) -> None:
    with (
        patch("app.services.ffmpeg_downloader.platform.system", return_value="Linux"),
        patch("app.services.ffmpeg_downloader.platform.machine", return_value="x86_64"),
        patch(
            "app.services.ffmpeg_downloader.urllib.request.urlopen",
            side_effect=urllib.error.URLError("offline"),
        ),
        pytest.raises(OSError, match="offline"),
    ):
        ffmpeg_downloader.download_and_extract_ffmpeg(data_root=tmp_path / "data")

    assert not (tmp_path / "data" / ffmpeg_downloader.FFMPEG_VERSION).exists()
