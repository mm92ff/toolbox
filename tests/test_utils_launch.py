import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services import system_utils as utils


class WindowsLaunchTests(unittest.TestCase):
    def test_merge_arguments_combines_shortcut_and_user_arguments(self) -> None:
        merged = utils._merge_arguments("--profile dev", "--safe")
        self.assertEqual("--profile dev --safe", merged)

    def test_merge_arguments_handles_empty_values(self) -> None:
        self.assertEqual("--safe", utils._merge_arguments("", "--safe"))
        self.assertEqual("--profile dev", utils._merge_arguments("--profile dev", ""))
        self.assertIsNone(utils._merge_arguments("", ""))

    def test_launch_path_with_advanced_options_uses_start_process_launcher(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tool_file = Path(temp_dir) / "tool.exe"
            tool_file.write_text("placeholder", encoding="utf-8")

            with (
                patch("app.services.system_utils.sys.platform", "win32"),
                patch(
                    "app.services.system_utils._launch_windows_with_start_process"
                ) as advanced_launcher,
            ):
                utils.launch_path(str(tool_file), arguments="--help")

        advanced_launcher.assert_called_once()

    def test_launch_path_uses_startfile_for_windows_script_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script_file = Path(temp_dir) / "convert.pyw"
            script_file.write_text("print('ok')", encoding="utf-8")

            with (
                patch("app.services.system_utils.sys.platform", "win32"),
                patch("app.services.system_utils.os.startfile", create=True) as startfile_mock,
            ):
                utils.launch_path(str(script_file))

        startfile_mock.assert_called_once_with(str(script_file))

    def test_launch_path_opens_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch(
                "app.services.system_utils.open_directory_in_os", return_value=True
            ) as open_directory:
                utils.launch_path(temp_dir, run_as_admin=True)

        open_directory.assert_called_once_with(temp_dir)

    def test_launch_windows_admin_uses_shortcut_target_when_available(self) -> None:
        shortcut = Path("C:/Links/tool.lnk")
        target = Path("C:/Apps/tool.exe")
        with (
            patch(
                "app.services.system_utils._resolve_windows_shortcut",
                return_value=(target, "--profile dev", "C:/Apps"),
            ) as resolve_shortcut,
            patch(
                "app.services.system_utils._shell_execute_windows", return_value=33
            ) as shell_execute,
        ):
            utils._launch_windows_admin(shortcut)

        resolve_shortcut.assert_called_once_with(shortcut)
        shell_execute.assert_called_once_with(
            "runas",
            str(target),
            "--profile dev",
            "C:/Apps",
            1,
        )

    def test_launch_windows_admin_falls_back_to_shortcut_when_unresolved(self) -> None:
        shortcut = Path("C:/Links/tool.lnk")
        with (
            patch(
                "app.services.system_utils._resolve_windows_shortcut",
                return_value=(None, None, None),
            ) as resolve_shortcut,
            patch(
                "app.services.system_utils._shell_execute_windows", return_value=33
            ) as shell_execute,
        ):
            utils._launch_windows_admin(shortcut)

        resolve_shortcut.assert_called_once_with(shortcut)
        shell_execute.assert_called_once_with(
            "runas",
            str(shortcut),
            None,
            str(shortcut.parent),
            1,
        )

    def test_resolve_windows_shortcut_parses_powershell_json(self) -> None:
        shortcut = Path("C:/Links/tool.lnk")
        completed = subprocess.CompletedProcess(
            args=["powershell"],
            returncode=0,
            stdout='{"target":"C:\\\\Apps\\\\tool.exe","arguments":"--safe","working_directory":"C:\\\\Apps"}',
            stderr="",
        )
        with (
            patch(
                "app.services.system_utils._resolve_system_command",
                return_value="C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
            ),
            patch("app.services.system_utils.subprocess.run", return_value=completed) as run_mock,
        ):
            target, arguments, working_directory = utils._resolve_windows_shortcut(shortcut)

        run_mock.assert_called_once()
        self.assertEqual(Path("C:/Apps/tool.exe"), target)
        self.assertEqual("--safe", arguments)
        self.assertEqual("C:\\Apps", working_directory)

    def test_launch_path_rejects_null_byte_in_path(self) -> None:
        with self.assertRaises(ValueError):
            utils.launch_path("C:/Tools/app.exe\x00")

    def test_path_log_label_cache_is_bounded(self) -> None:
        utils.clear_system_utils_caches()
        for index in range(2500):
            utils._path_log_label(f"C:/Users/tester/Desktop/tool_{index}.exe")

        info = utils._path_log_label_cached.cache_info()
        self.assertEqual(2048, info.maxsize)
        self.assertLessEqual(info.currsize, 2048)


if __name__ == "__main__":
    unittest.main()
