from unittest.mock import MagicMock, patch
import pytest

from app.services.file_associations import (
    _extension_group,
    open_with_file_associations,
)


def test_extension_group_audio():
    assert _extension_group("song.mp3") == "audio"
    assert _extension_group("track.flac") == "audio"
    assert _extension_group("sound.WAV") == "audio"  # case-insensitive


def test_extension_group_video():
    assert _extension_group("movie.mp4") == "video"
    assert _extension_group("clip.MKV") == "video"


def test_extension_group_image():
    assert _extension_group("photo.jpg") == "image"
    assert _extension_group("icon.PNG") == "image"


def test_extension_group_pdf():
    assert _extension_group("doc.pdf") == "pdf"
    assert _extension_group("doc.PDF") == "pdf"


def test_extension_group_document():
    assert _extension_group("report.docx") == "document"
    assert _extension_group("sheet.xlsx") == "document"
    assert _extension_group("presentation.odp") == "document"


def test_extension_group_unknown():
    assert _extension_group("binary.exe") is None
    assert _extension_group("script.sh") is None
    assert _extension_group("noext") is None


def test_open_with_system_linux():
    with patch("app.services.file_associations.sys") as mock_sys, \
         patch("app.services.file_associations.subprocess.Popen") as mock_popen:
        mock_sys.platform = "linux"
        result = open_with_file_associations(
            "/home/user/song.mp3",
            use_system=True,
            audio_app="vlc",
            video_app="",
            image_app="",
            pdf_app="",
            document_app="",
        )
        assert result is True
        mock_popen.assert_called_once_with(["xdg-open", "/home/user/song.mp3"])


def test_open_with_custom_app():
    with patch("app.services.file_associations.subprocess.Popen") as mock_popen:
        result = open_with_file_associations(
            "/home/user/song.mp3",
            use_system=False,
            audio_app="vlc",
            video_app="",
            image_app="",
            pdf_app="",
            document_app="",
        )
        assert result is True
        mock_popen.assert_called_once_with(["vlc", "/home/user/song.mp3"])


def test_open_falls_back_to_system_when_no_custom_app():
    with patch("app.services.file_associations.sys") as mock_sys, \
         patch("app.services.file_associations.subprocess.Popen") as mock_popen:
        mock_sys.platform = "linux"
        result = open_with_file_associations(
            "/home/user/song.mp3",
            use_system=False,
            audio_app="",   # empty -> fallback
            video_app="",
            image_app="",
            pdf_app="",
            document_app="",
        )
        assert result is True
        mock_popen.assert_called_once_with(["xdg-open", "/home/user/song.mp3"])


def test_open_returns_false_for_unknown_extension():
    result = open_with_file_associations(
        "/home/user/script.sh",
        use_system=False,
        audio_app="vlc",
        video_app="",
        image_app="",
        pdf_app="",
        document_app="",
    )
    assert result is False


def test_open_with_multiword_custom_app():
    with patch("app.services.file_associations.subprocess.Popen") as mock_popen:
        result = open_with_file_associations(
            "/home/user/video.mp4",
            use_system=False,
            audio_app="",
            video_app="flatpak run org.videolan.VLC",
            image_app="",
            pdf_app="",
            document_app="",
        )
        assert result is True
        mock_popen.assert_called_once_with(["flatpak", "run", "org.videolan.VLC", "/home/user/video.mp4"])
