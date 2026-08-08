from unittest.mock import patch
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
         patch("app.services.file_associations.shutil.which", return_value="/usr/bin/xdg-open"), \
         patch("app.services.file_associations.external_process_environment", return_value={"SAFE": "1"}), \
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
        mock_popen.assert_called_once_with(
            ["/usr/bin/xdg-open", "/home/user/song.mp3"],
            shell=False,
            env={"SAFE": "1"},
        )


def test_open_with_custom_app():
    with patch("app.services.file_associations.shutil.which", return_value="/usr/bin/vlc"), \
         patch("app.services.file_associations.external_process_environment", return_value={"SAFE": "1"}), \
         patch("app.services.file_associations.subprocess.Popen") as mock_popen:
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
        mock_popen.assert_called_once_with(
            ["/usr/bin/vlc", "/home/user/song.mp3"],
            shell=False,
            env={"SAFE": "1"},
        )


def test_empty_custom_app_fails_without_silent_system_fallback():
    with (
        patch("app.services.file_associations.subprocess.Popen") as mock_popen,
        pytest.raises(OSError, match="No custom application"),
    ):
        open_with_file_associations(
            "/home/user/song.mp3",
            use_system=False,
            audio_app="",
            video_app="",
            image_app="",
            pdf_app="",
            document_app="",
        )
    mock_popen.assert_not_called()


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
    with patch("app.services.file_associations.shutil.which", return_value="/usr/bin/flatpak"), \
         patch("app.services.file_associations.external_process_environment", return_value={"SAFE": "1"}), \
         patch("app.services.file_associations.subprocess.Popen") as mock_popen:
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
        mock_popen.assert_called_once_with(
            ["/usr/bin/flatpak", "run", "org.videolan.VLC", "/home/user/video.mp4"],
            shell=False,
            env={"SAFE": "1"},
        )


def test_invalid_custom_application_raises_useful_error():
    with patch("app.services.file_associations.shutil.which", return_value=None):
        with pytest.raises(OSError, match="missing-player"):
            open_with_file_associations(
                "/home/user/song.mp3",
                use_system=False,
                audio_app="missing-player",
                video_app="",
                image_app="",
                pdf_app="",
                document_app="",
            )


def test_custom_app_receives_absolute_path_with_spaces_and_leading_dash(tmp_path):
    source = tmp_path / "- leading name.mp3"
    source.write_bytes(b"audio")
    with (
        patch("app.services.file_associations.shutil.which", return_value="/usr/bin/vlc"),
        patch(
            "app.services.file_associations.external_process_environment",
            return_value={"SAFE": "1"},
        ),
        patch("app.services.file_associations.subprocess.Popen") as mock_popen,
    ):
        open_with_file_associations(
            str(source),
            use_system=False,
            audio_app="vlc --play-and-exit",
            video_app="",
            image_app="",
            pdf_app="",
            document_app="",
        )

    mock_popen.assert_called_once_with(
        ["/usr/bin/vlc", "--play-and-exit", str(source.resolve())],
        shell=False,
        env={"SAFE": "1"},
    )


def test_invalid_custom_quotes_fail_before_process_start(tmp_path):
    source = tmp_path / "song.mp3"
    source.write_bytes(b"audio")
    with (
        patch("app.services.file_associations.subprocess.Popen") as mock_popen,
        pytest.raises(OSError, match="No closing quotation"),
    ):
        open_with_file_associations(
            str(source),
            use_system=False,
            audio_app='vlc "unterminated',
            video_app="",
            image_app="",
            pdf_app="",
            document_app="",
        )
    mock_popen.assert_not_called()
