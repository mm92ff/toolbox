import os
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets

from app import constants
from app.services.image_thumbnails import load_or_create_thumbnail


def _ensure_app() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_thumbnail_cache_persists_between_calls() -> None:
    _ensure_app()
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        source = base / "sample.png"
        cache_dir = base / "thumb-cache"

        pixmap = QtGui.QPixmap(320, 180)
        pixmap.fill(QtGui.QColor("#336699"))
        assert pixmap.save(str(source), "PNG")

        first = load_or_create_thumbnail(
            str(source),
            72,
            constants.IMAGE_PREVIEW_MODE_FIT,
            cache_dir,
        )
        assert first is not None
        assert not first.isNull()
        assert first.size() == QtCore.QSize(72, 72)

        cache_files = list(cache_dir.glob("*.png"))
        assert len(cache_files) == 2
        first_mtimes = {path.name: path.stat().st_mtime_ns for path in cache_files}

        second = load_or_create_thumbnail(
            str(source),
            72,
            constants.IMAGE_PREVIEW_MODE_FIT,
            cache_dir,
        )
        assert second is not None
        assert not second.isNull()
        assert second.size() == QtCore.QSize(72, 72)
        second_cache_files = list(cache_dir.glob("*.png"))
        assert len(second_cache_files) == 2
        second_mtimes = {path.name: path.stat().st_mtime_ns for path in second_cache_files}
        assert second_mtimes == first_mtimes


def test_thumbnail_fill_mode_outputs_square_thumbnail() -> None:
    _ensure_app()
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        source = base / "portrait.png"
        cache_dir = base / "thumb-cache"

        pixmap = QtGui.QPixmap(120, 360)
        pixmap.fill(QtGui.QColor("#aa3377"))
        assert pixmap.save(str(source), "PNG")

        thumb = load_or_create_thumbnail(
            str(source),
            96,
            constants.IMAGE_PREVIEW_MODE_FILL,
            cache_dir,
        )
        assert thumb is not None
        assert not thumb.isNull()
        assert thumb.size() == QtCore.QSize(96, 96)
