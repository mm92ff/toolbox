from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_linux_spec_is_onedir_and_does_not_autodetect_ffmpeg() -> None:
    spec_text = (PROJECT_ROOT / "toolbox_linux.spec").read_text(encoding="utf-8")

    assert "exclude_binaries=True" in spec_text
    assert "COLLECT(" in spec_text
    assert "exclude_system_libraries()" in spec_text
    assert "shutil.which" not in spec_text
    assert "TOOLBOX_FFMPEG_BINARY" in spec_text


def test_apprun_and_build_scripts_are_executable() -> None:
    paths = (
        PROJECT_ROOT / "packaging" / "linux" / "AppRun",
        PROJECT_ROOT / "scripts" / "build-appimage.sh",
        PROJECT_ROOT / "scripts" / "test-appdir.sh",
        PROJECT_ROOT / "scripts" / "test-appimage.sh",
        PROJECT_ROOT / "scripts" / "check-elf-dependencies.sh",
        PROJECT_ROOT / "scripts" / "check-appimage-content.sh",
        PROJECT_ROOT / "scripts" / "verify-linux-release.sh",
        PROJECT_ROOT / "scripts" / "check-pyinstaller-warnings.sh",
        PROJECT_ROOT / "scripts" / "compare-appimage-contents.sh",
        PROJECT_ROOT / "scripts" / "test-x11-desktop.sh",
    )

    for path in paths:
        mode = path.stat().st_mode
        assert mode & stat.S_IXUSR, f"{path} must be executable"


def test_apprun_uses_relative_appdir_and_forwards_arguments() -> None:
    app_run = (PROJECT_ROOT / "packaging" / "linux" / "AppRun").read_text(
        encoding="utf-8"
    )

    assert "TOOLBOX_APPDIR" in app_run
    assert 'exec "$TOOLBOX_APPDIR/usr/lib/toolbox/toolbox" "$@"' in app_run
    assert "LD_LIBRARY_PATH=" not in app_run


def test_custom_qt_hook_excludes_broken_tiff_plugin() -> None:
    hook = (
        PROJECT_ROOT
        / "packaging"
        / "pyinstaller-hooks"
        / "hook-PySide6.QtGui.py"
    ).read_text(encoding="utf-8")

    assert "libqtiff.so" in hook


def test_desktop_file_is_valid() -> None:
    desktop_file = PROJECT_ROOT / "packaging" / "linux" / "toolbox.desktop"
    completed = subprocess.run(
        ["desktop-file-validate", str(desktop_file)],
        check=False,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
    )

    assert completed.returncode == 0, completed.stderr or completed.stdout


def test_build_requirements_are_pinned() -> None:
    requirements = (
        PROJECT_ROOT / "requirements-build-linux.txt"
    ).read_text(encoding="utf-8")

    assert "PySide6==" in requirements
    assert "pytest==" in requirements
    assert "pyinstaller==" in requirements


def test_build_script_packages_license_and_build_information() -> None:
    build_script = (PROJECT_ROOT / "scripts" / "build-appimage.sh").read_text(
        encoding="utf-8"
    )

    assert "THIRD_PARTY_NOTICES.md" in build_script
    assert "PYTHON-LICENSE.txt" in build_script
    assert 'sysconfig.get_path("stdlib")' in build_script
    assert "PYINSTALLER-COPYING.txt" in build_script
    assert "APPIMAGE-RUNTIME-LICENSE.txt" in build_script
    assert "ICU-LICENSE.txt" in build_script
    assert "LGPL-3.txt" in build_script
    assert "build-info.txt" in build_script


def test_build_script_validates_metadata_without_network_access() -> None:
    build_script = (PROJECT_ROOT / "scripts" / "build-appimage.sh").read_text(
        encoding="utf-8"
    )

    assert "appstreamcli validate --no-net" in build_script
    assert "--no-appstream" in build_script


def test_build_script_pins_appimagetool_and_creates_portable_checksum() -> None:
    build_script = (PROJECT_ROOT / "scripts" / "build-appimage.sh").read_text(
        encoding="utf-8"
    )
    pinned_checksum = (
        PROJECT_ROOT / "packaging" / "linux" / "appimagetool-x86_64.sha256"
    ).read_text(encoding="utf-8")

    assert len(pinned_checksum.split()[0]) == 64
    assert "ACTUAL_APPIMAGETOOL_SHA256" in build_script
    assert "EXPECTED_APPIMAGETOOL_SHA256" in build_script
    assert 'cd "$OUTPUT_DIR"' in build_script
    assert 'sha256sum "$(basename "$OUTPUT")"' in build_script
    assert "SOURCE_DATE_EPOCH" in build_script
    assert "PYTHONHASHSEED" in build_script
    assert "--mksquashfs-opt=-processors" in build_script
    assert "--mksquashfs-opt=-all-time" in build_script


def test_appimage_acceptance_covers_content_relocation_and_xcb() -> None:
    build_script = (PROJECT_ROOT / "scripts" / "build-appimage.sh").read_text(
        encoding="utf-8"
    )
    image_test = (PROJECT_ROOT / "scripts" / "test-appimage.sh").read_text(
        encoding="utf-8"
    )
    content_test = (
        PROJECT_ROOT / "scripts" / "check-appimage-content.sh"
    ).read_text(encoding="utf-8")

    assert "check-appimage-content.sh" in build_script
    assert "check-pyinstaller-warnings.sh" in build_script
    assert "Renamed Toolbox.AppImage" in image_test
    assert "Toolbox Link.AppImage" in image_test
    assert "read-only-directory-token" in image_test
    assert "QT_SCALE_FACTOR=2" in image_test
    assert "QT_QPA_PLATFORM=xcb" in image_test
    assert "test-x11-desktop.sh" in build_script
    assert "--appimage-extract" in content_test
    assert ".pytest_cache" in content_test
    assert "*.bat" in content_test
    assert "libc.so" in content_test


def test_reproducibility_check_compares_content_modes_and_symlinks() -> None:
    comparison_script = (
        PROJECT_ROOT / "scripts" / "compare-appimage-contents.sh"
    ).read_text(encoding="utf-8")

    assert "--appimage-extract" in comparison_script
    assert "sha256sum" in comparison_script
    assert "symlink %p -> %l" in comparison_script
    assert "mode %m %y %p" in comparison_script


def test_x11_acceptance_checks_window_identity_resize_and_xdg_state() -> None:
    x11_test = (PROJECT_ROOT / "scripts" / "test-x11-desktop.sh").read_text(
        encoding="utf-8"
    )

    assert "toolbox.Toolbox" in x11_test
    assert "_NET_WM_ICON" in x11_test
    assert "TARGET_WIDTH" in x11_test
    assert "XDG_CONFIG_HOME" in x11_test
