from __future__ import annotations

import subprocess
from pathlib import Path

from app.services.desktop_entries import expand_desktop_exec, read_desktop_entry


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_development_desktop_is_valid_and_portable() -> None:
    desktop_file = PROJECT_ROOT / "Toolbox.desktop"
    completed = subprocess.run(
        ["desktop-file-validate", str(desktop_file)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout

    metadata = read_desktop_entry(desktop_file, locale_name="de_DE")
    assert metadata.name == "Toolbox"
    assert metadata.try_exec == "/usr/bin/python3"
    assert metadata.working_directory == ""
    assert "%k" in metadata.exec_line
    assert ".venv/bin/python" in metadata.exec_line
    assert "/home/" not in metadata.exec_line
    command = expand_desktop_exec(metadata)
    assert command[0] == "/usr/bin/python3"
    assert command[-1] == str(desktop_file.resolve())


def test_backup_desktop_is_valid_and_portable() -> None:
    desktop_file = PROJECT_ROOT / "Toolbox-Code-Backup.desktop"
    completed = subprocess.run(
        ["desktop-file-validate", str(desktop_file)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout

    metadata = read_desktop_entry(desktop_file, locale_name="de_DE")
    assert metadata.try_exec == "/usr/bin/python3"
    assert metadata.working_directory == ""
    assert "%k" in metadata.exec_line
    assert "scripts/create_code_backup.sh" in metadata.exec_line
    assert "/home/" not in metadata.exec_line
    command = expand_desktop_exec(metadata)
    assert command[0] == "/usr/bin/python3"
    assert command[-1] == str(desktop_file.resolve())
