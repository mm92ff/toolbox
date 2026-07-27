from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from app.services import system_utils as utils


def test_external_process_environment_restores_original_library_path() -> None:
    with (
        patch("app.services.system_utils.sys.platform", "linux"),
        patch.object(utils.sys, "frozen", True, create=True),
        patch.dict(
            os.environ,
            {
                "LD_LIBRARY_PATH": "/tmp/toolbox-bundle",
                "LD_LIBRARY_PATH_ORIG": "/usr/local/lib",
                "TOOLBOX_TEST_VALUE": "kept",
            },
            clear=True,
        ),
    ):
        env = utils.external_process_environment("/usr/bin/true")

    assert env["LD_LIBRARY_PATH"] == "/usr/local/lib"
    assert env["LD_LIBRARY_PATH_ORIG"] == "/usr/local/lib"
    assert env["TOOLBOX_TEST_VALUE"] == "kept"


def test_external_process_environment_removes_injected_library_path_without_original() -> None:
    with (
        patch("app.services.system_utils.sys.platform", "linux"),
        patch.object(utils.sys, "frozen", True, create=True),
        patch.dict(os.environ, {"LD_LIBRARY_PATH": "/tmp/toolbox-bundle"}, clear=True),
    ):
        env = utils.external_process_environment("/usr/bin/true")

    assert "LD_LIBRARY_PATH" not in env


def test_external_process_environment_treats_empty_original_as_unset() -> None:
    original_environment = {
        "LD_LIBRARY_PATH": "/tmp/toolbox-bundle",
        "LD_LIBRARY_PATH_ORIG": "",
        "TOOLBOX_TEST_VALUE": "unchanged",
    }
    with (
        patch("app.services.system_utils.sys.platform", "linux"),
        patch.object(utils.sys, "frozen", True, create=True),
        patch.dict(os.environ, original_environment, clear=True),
    ):
        env = utils.external_process_environment("/usr/bin/true")
        assert os.environ == original_environment

    assert "LD_LIBRARY_PATH" not in env
    assert env["LD_LIBRARY_PATH_ORIG"] == ""
    assert env["TOOLBOX_TEST_VALUE"] == "unchanged"


def test_source_process_environment_is_not_modified_without_pyinstaller_marker() -> None:
    with (
        patch("app.services.system_utils.sys.platform", "linux"),
        patch.object(utils.sys, "frozen", False, create=True),
        patch.dict(
            os.environ,
            {"LD_LIBRARY_PATH": "/development/library/path"},
            clear=True,
        ),
    ):
        env = utils.external_process_environment("/usr/bin/true")

    assert env["LD_LIBRARY_PATH"] == "/development/library/path"


def test_bundled_helper_keeps_bundle_library_path() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        helper = Path(temp_dir) / "ffmpeg"
        helper.write_text("#!/bin/sh\n", encoding="utf-8")
        with (
            patch("app.services.system_utils.sys.platform", "linux"),
            patch.object(utils.sys, "frozen", True, create=True),
            patch.object(utils.sys, "_MEIPASS", temp_dir, create=True),
            patch.dict(os.environ, {"LD_LIBRARY_PATH": temp_dir}, clear=True),
        ):
            env = utils.external_process_environment(helper)

    assert env["LD_LIBRARY_PATH"] == temp_dir


def test_launch_linux_executable_passes_arguments_workdir_and_clean_environment() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        executable = root / "tool with spaces"
        executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        executable.chmod(0o755)
        workdir = root / "working directory"
        workdir.mkdir()

        with (
            patch("app.services.system_utils.sys.platform", "linux"),
            patch.object(utils.sys, "frozen", True, create=True),
            patch.dict(
                os.environ,
                {
                    "LD_LIBRARY_PATH": "/tmp/toolbox-bundle",
                    "LD_LIBRARY_PATH_ORIG": "/usr/lib",
                },
                clear=True,
            ),
            patch("app.services.system_utils.subprocess.Popen") as popen,
        ):
            utils.launch_path(
                str(executable),
                arguments='--name "two words" --literal "$HOME;$(false)"',
                working_directory=str(workdir),
            )

    popen.assert_called_once()
    args, kwargs = popen.call_args
    assert args[0] == [
        str(executable),
        "--name",
        "two words",
        "--literal",
        "$HOME;$(false)",
    ]
    assert kwargs["cwd"] == str(workdir)
    assert kwargs["shell"] is False
    assert kwargs["env"]["LD_LIBRARY_PATH"] == "/usr/lib"


def test_launch_linux_wait_reaps_process_without_blocking_caller() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executable = Path(temp_dir) / "tool"
        executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        executable.chmod(0o755)

        with (
            patch("app.services.system_utils.sys.platform", "linux"),
            patch("app.services.system_utils.subprocess.Popen") as popen,
            patch("app.services.system_utils.threading.Thread") as thread,
        ):
            popen.return_value.pid = 1234
            utils.launch_path(str(executable), wait=True)

    popen.assert_called_once()
    assert popen.call_args.kwargs["shell"] is False
    thread.assert_called_once_with(
        target=popen.return_value.wait,
        name="toolbox-wait-1234",
        daemon=True,
    )
    thread.return_value.start.assert_called_once_with()


def test_launch_linux_document_uses_desktop_opener() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        document = Path(temp_dir) / "notes.txt"
        document.write_text("hello", encoding="utf-8")

        with (
            patch("app.services.system_utils.sys.platform", "linux"),
            patch(
                "app.services.system_utils._desktop_open_command",
                return_value=["/usr/bin/xdg-open", str(document)],
            ),
            patch("app.services.system_utils.subprocess.run") as run,
        ):
            utils.launch_path(str(document))

    run.assert_called_once()
    assert run.call_args.args[0] == ["/usr/bin/xdg-open", str(document)]
    assert run.call_args.kwargs["shell"] is False
    assert isinstance(run.call_args.kwargs["env"], dict)


def test_launch_linux_document_rejects_process_arguments() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        document = Path(temp_dir) / "notes.txt"
        document.write_text("hello", encoding="utf-8")

        with patch("app.services.system_utils.sys.platform", "linux"):
            with pytest.raises(OSError, match="require an executable"):
                utils.launch_path(str(document), arguments="--unsupported")


def test_launch_linux_desktop_shortcut_uses_direct_monitored_command() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        shortcut = Path(temp_dir) / "Application Shortcut.desktop"
        shortcut.write_text(
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=Test shortcut\n"
            "Exec=/usr/bin/true\n",
            encoding="utf-8",
        )
        shortcut.chmod(0o755)

        with (
            patch("app.services.system_utils.sys.platform", "linux"),
            patch("app.services.system_utils.subprocess.run") as run,
            patch("app.services.system_utils.subprocess.Popen") as popen,
        ):
            utils.launch_path(str(shortcut))

    run.assert_not_called()
    popen.assert_called_once()
    assert popen.call_args.args[0] == ("/usr/bin/true",)
    assert popen.call_args.kwargs["cwd"] == str(shortcut.parent)
    assert popen.call_args.kwargs["shell"] is False
    assert popen.call_args.kwargs["start_new_session"] is True


def test_launch_linux_desktop_shortcut_rejects_custom_arguments() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        shortcut = Path(temp_dir) / "shortcut.desktop"
        shortcut.write_text(
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=Test shortcut\n"
            "Exec=/usr/bin/true\n",
            encoding="utf-8",
        )
        shortcut.chmod(0o755)

        with patch("app.services.system_utils.sys.platform", "linux"):
            with pytest.raises(OSError, match="not supported.*\\.desktop"):
                utils.launch_path(str(shortcut), arguments="--unsafe-assumption")


def test_launch_linux_desktop_shortcut_with_real_gio() -> None:
    gio = shutil.which("gio")
    if gio is None:
        pytest.skip("gio is not installed")

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        marker = root / "desktop-launch-marker"
        shortcut = root / "Harmless Test.desktop"
        shortcut.write_text(
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=Harmless Toolbox test\n"
            f"Exec=/usr/bin/touch {marker}\n"
            "Terminal=false\n",
            encoding="utf-8",
        )
        shortcut.chmod(0o755)

        with patch("app.services.system_utils.sys.platform", "linux"):
            utils.launch_path(str(shortcut))

        deadline = time.monotonic() + 2.0
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.01)

        assert marker.is_file()


def test_launch_linux_rejects_missing_working_directory() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executable = Path(temp_dir) / "tool"
        executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        executable.chmod(0o755)

        with patch("app.services.system_utils.sys.platform", "linux"):
            with pytest.raises(NotADirectoryError):
                utils.launch_path(
                    str(executable),
                    working_directory=str(Path(temp_dir) / "missing"),
                )


def test_launch_linux_rejects_malformed_argument_quoting() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executable = Path(temp_dir) / "tool"
        executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        executable.chmod(0o755)

        with patch("app.services.system_utils.sys.platform", "linux"):
            with pytest.raises(ValueError, match="No closing quotation"):
                utils.launch_path(str(executable), arguments='"unterminated')


def test_launch_linux_rejects_windows_admin_option() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executable = Path(temp_dir) / "tool"
        executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        executable.chmod(0o755)

        with patch("app.services.system_utils.sys.platform", "linux"):
            with pytest.raises(OSError, match="only supported on Windows"):
                utils.launch_path(str(executable), run_as_admin=True)


def test_desktop_open_command_falls_back_to_gio() -> None:
    target = Path("/tmp/example")

    def which(command: str) -> str | None:
        return "/usr/bin/gio" if command == "gio" else None

    with patch("app.services.system_utils.shutil.which", side_effect=which):
        command = utils._desktop_open_command(target)

    assert command == ["/usr/bin/gio", "open", str(target)]


def test_completed_process_type_remains_available_for_test_doubles() -> None:
    completed = subprocess.CompletedProcess(args=["true"], returncode=0)
    assert completed.returncode == 0
