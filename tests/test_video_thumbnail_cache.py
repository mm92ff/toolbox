import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets

from app import constants
from app.services import video_thumbnails


def _ensure_app() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_video_thumbnail_cache_hit_without_ffmpeg(monkeypatch) -> None:
    _ensure_app()
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        source = base / "clip.mp4"
        source.write_bytes(b"dummy")
        cache_dir = base / "video-cache"

        cache_path = video_thumbnails._cache_path_for(
            source, 72, constants.IMAGE_PREVIEW_MODE_FIT, cache_dir
        )
        assert cache_path is not None
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        pixmap = QtGui.QPixmap(72, 72)
        pixmap.fill(QtGui.QColor("#224466"))
        assert pixmap.save(str(cache_path), "PNG")

        monkeypatch.setattr(video_thumbnails.shutil, "which", lambda _name: None)
        result = video_thumbnails.load_or_create_video_thumbnail(
            str(source),
            72,
            constants.IMAGE_PREVIEW_MODE_FIT,
            cache_dir,
        )
        assert result is not None
        assert not result.isNull()
        assert result.size() == QtCore.QSize(72, 72)


def test_video_thumbnail_returns_none_without_ffmpeg_or_cache(monkeypatch) -> None:
    _ensure_app()
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        source = base / "clip.mp4"
        source.write_bytes(b"dummy")

        monkeypatch.setattr(video_thumbnails, "_find_ffmpeg_path", lambda: None)
        result = video_thumbnails.load_or_create_video_thumbnail(
            str(source),
            64,
            constants.IMAGE_PREVIEW_MODE_FILL,
            base / "video-cache",
        )
        assert result is None


def test_video_thumbnail_generates_normal_and_hq_cache_variants(monkeypatch) -> None:
    _ensure_app()
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        source = base / "clip.mp4"
        source.write_bytes(b"dummy")
        cache_dir = base / "video-cache"

        call_count = {"extract": 0}

        def _fake_extract(_source: Path, _ffmpeg_path: str, _capture_seconds: float) -> QtGui.QPixmap:
            call_count["extract"] += 1
            pixmap = QtGui.QPixmap(320, 180)
            pixmap.fill(QtGui.QColor("#446688"))
            return pixmap

        monkeypatch.setattr(video_thumbnails, "_find_ffmpeg_path", lambda: "ffmpeg")
        monkeypatch.setattr(video_thumbnails, "_extract_video_frame", _fake_extract)

        result = video_thumbnails.load_or_create_video_thumbnail(
            str(source),
            72,
            constants.IMAGE_PREVIEW_MODE_FIT,
            cache_dir,
        )
        assert result is not None
        assert not result.isNull()
        assert result.size() == QtCore.QSize(72, 72)
        assert call_count["extract"] == 1

        cache_files = list(cache_dir.glob("*.png"))
        assert len(cache_files) == 2
