from __future__ import annotations

import stat
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_deb_scripts_are_executable() -> None:
    for relative_path in ("scripts/build-deb.sh", "scripts/test-deb.sh"):
        path = PROJECT_ROOT / relative_path
        assert path.stat().st_mode & stat.S_IXUSR


def test_deb_build_uses_verified_appimage_payload_and_native_paths() -> None:
    script = (PROJECT_ROOT / "scripts" / "build-deb.sh").read_text(
        encoding="utf-8"
    )

    assert 'PACKAGE_NAME=toolbox-launcher' in script
    assert 'ARCHITECTURE=amd64' in script
    assert '--appimage-extract' in script
    assert 'dpkg-deb --root-owner-group' in script
    assert 'usr/lib/toolbox/_internal/$MEDIA_BINARY' in script
    assert 'X-Toolbox-AppImage-SHA256' in script
    assert 'libfuse' not in script


def test_deb_acceptance_checks_dependencies_content_and_startup() -> None:
    script = (PROJECT_ROOT / "scripts" / "test-deb.sh").read_text(
        encoding="utf-8"
    )

    assert 'dpkg-deb --extract' in script
    assert 'dpkg-deb --control' in script
    assert 'libfuse' in script
    assert 'usr/bin/ffmpeg' in script
    assert 'usr/lib/toolbox/_internal/ffmpeg' in script
    assert 'libxcb-cursor.so.0' in script
    assert 'libxkbcommon-x11.so.0' in script
    assert '--deb-smoke-token' in script
    assert 'QT_QPA_PLATFORM=offscreen' in script
