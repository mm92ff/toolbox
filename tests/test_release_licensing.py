from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_toolbox_license_and_third_party_notice_are_separated() -> None:
    license_text = (PROJECT_ROOT / "LICENSE").read_text(encoding="utf-8")
    notice = (PROJECT_ROOT / "NOTICE").read_text(encoding="utf-8")

    assert license_text.startswith("MIT License")
    assert "Toolbox source code is licensed under the MIT License" in notice
    assert "FFmpeg and\nFFprobe" in notice
    assert "GNU Lesser General Public License version 2.1" in notice
    assert "THIRD_PARTY_NOTICES.md" in notice


def test_ffmpeg_notice_matches_the_reviewed_linux_payload() -> None:
    notices = (PROJECT_ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")

    assert "Toolbox reproducible build of FFmpeg `7.0.2`" in notices
    assert "ffmpeg.org/releases/ffmpeg-7.0.2.tar.xz" in notices
    assert "GNU Lesser General Public License version 2.1 or later" in notices
    assert "--disable-gpl" in notices
    assert "--disable-nonfree" in notices
    assert "Toolbox-0.45-beta-ffmpeg-7.0.2-source.tar.xz" in notices
    assert "johnvansickle" not in notices.lower()
    assert "gyan.dev" not in notices.lower()


def test_readme_describes_windows_linux_and_bundled_ffmpeg() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert "| Windows | Python source and PyInstaller `.exe`" in readme
    assert "| Linux | Python source, AppImage, and native `.deb`" in readme
    assert "Official AppImage and DEB releases always contain" in readme
    assert "build-bundled-ffmpeg.sh" in readme
    assert "corresponding-source" in readme
    assert "AppImage does not bundle FFmpeg" not in readme


def test_release_verifier_requires_corresponding_source() -> None:
    verifier = (PROJECT_ROOT / "scripts" / "verify-linux-release.sh").read_text(encoding="utf-8")

    assert "FFMPEG_SOURCE_BUNDLE" in verifier
    assert "FFMPEG_RUNTIME_BUNDLE" in verifier
    assert "Corresponding FFmpeg source release is missing" in verifier
    assert "sha256sum -c" in verifier
