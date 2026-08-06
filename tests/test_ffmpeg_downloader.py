import platform
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from app.services.ffmpeg_downloader import download_and_extract_ffmpeg

@pytest.fixture
def mock_temp_dir(tmp_path):
    with patch("app.services.ffmpeg_downloader.tempfile.TemporaryDirectory") as mock_tmp:
        mock_tmp.return_value.__enter__.return_value = str(tmp_path)
        yield tmp_path

@pytest.fixture
def mock_bin_dir(tmp_path):
    bin_dir = tmp_path / ".bin"
    with patch("app.services.ffmpeg_downloader.PROJECT_ROOT", tmp_path):
        yield bin_dir

@patch("app.services.ffmpeg_downloader.urllib.request.urlretrieve")
@patch("app.services.ffmpeg_downloader.tarfile.open")
def test_download_linux(mock_tar_open, mock_urlretrieve, mock_temp_dir, mock_bin_dir):
    with patch("platform.system", return_value="Linux"):
        # Setup mock tarfile behavior to not throw errors
        mock_tar = MagicMock()
        mock_tar_open.return_value.__enter__.return_value = mock_tar
        mock_tar.getmembers.return_value = []
        
        # We need to simulate the file existing so `target.exists()` passes
        (mock_bin_dir / "ffmpeg").parent.mkdir(parents=True, exist_ok=True)
        (mock_bin_dir / "ffmpeg").touch()

        result = download_and_extract_ffmpeg()
        
        assert result == mock_bin_dir / "ffmpeg"
        mock_urlretrieve.assert_called_once()
        assert mock_urlretrieve.call_args[0][0].endswith(".tar.xz")
        mock_tar_open.assert_called_once()

@patch("app.services.ffmpeg_downloader.urllib.request.urlretrieve")
@patch("app.services.ffmpeg_downloader.zipfile.ZipFile")
def test_download_windows(mock_zip_open, mock_urlretrieve, mock_temp_dir, mock_bin_dir):
    with patch("platform.system", return_value="Windows"):
        # Setup mock zipfile behavior
        mock_zip = MagicMock()
        mock_zip_open.return_value.__enter__.return_value = mock_zip
        mock_zip.namelist.return_value = []
        
        (mock_bin_dir / "ffmpeg.exe").parent.mkdir(parents=True, exist_ok=True)
        (mock_bin_dir / "ffmpeg.exe").touch()

        result = download_and_extract_ffmpeg()
        
        assert result == mock_bin_dir / "ffmpeg.exe"
        mock_urlretrieve.assert_called_once()
        assert mock_urlretrieve.call_args[0][0].endswith(".zip")
        mock_zip_open.assert_called_once()
