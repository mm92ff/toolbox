from __future__ import annotations

import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from app.services.desktop_entries import read_desktop_entry


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DESKTOP_FILE = PROJECT_ROOT / "Toolbox-Code-Backup.desktop"
BACKUP_SCRIPT = PROJECT_ROOT / "scripts" / "create_code_backup.sh"


def test_backup_desktop_targets_toolbox_script() -> None:
    metadata = read_desktop_entry(DESKTOP_FILE, locale_name="de_DE")

    assert metadata.name == "Toolbox Code-Backup"
    assert metadata.icon == "document-save"
    assert metadata.terminal is False
    assert "%k" in metadata.exec_line
    assert "scripts/create_code_backup.sh" in metadata.exec_line
    assert metadata.working_directory == ""
    assert "/home/" not in metadata.exec_line
    assert "clauodexi" not in DESKTOP_FILE.read_text(encoding="utf-8").lower()


def test_linux_backup_script_is_executable_and_syntax_valid() -> None:
    mode = BACKUP_SCRIPT.stat().st_mode
    assert mode & stat.S_IXUSR
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("bash is unavailable")

    completed = subprocess.run(
        [bash, "-n", str(BACKUP_SCRIPT)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_linux_backup_script_uses_toolbox_paths_and_exclusions() -> None:
    script = BACKUP_SCRIPT.read_text(encoding="utf-8")

    assert 'BACKUP_PREFIX="toolbox_code"' in script
    assert "Toolbox-Code-Backup.desktop" in script
    assert "scripts/build-appimage.sh" in script
    assert "scripts/build-bundled-ffmpeg.sh" in script
    assert "scripts/build-deb.sh" in script
    assert "dist-appimage" in script
    assert "dist-deb" in script
    assert "dist-source" in script
    assert "Toolbox.AppDir" in script
    assert "'-xr!thirdparty'" in script
    assert "'-xr!.bin'" in script
    assert "*.AppImage" in script
    assert "*.deb" in script
    assert ".toolbox-backup-tmp-" in script
    assert "--self-test" in script
    assert "clauodexi" not in script.lower()


def test_windows_backup_script_matches_linux_build_exclusions() -> None:
    script = (PROJECT_ROOT / "create-project-backup.bat").read_text(encoding="utf-8")

    assert "-xr!dist-appimage" in script
    assert "-xr!dist-deb" in script
    assert "-xr!dist-source" in script
    assert "-xr!Toolbox.AppDir" in script
    assert "-xr!thirdparty" in script
    assert "-xr!.bin" in script
    assert "-xr!*.AppImage" in script
    assert "*.deb" in script
    assert "Toolbox-Code-Backup.desktop" in script
    assert "scripts\\create_code_backup.sh" in script
