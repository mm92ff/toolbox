import tempfile
import unittest
from pathlib import Path

from app.services.paths import resolve_supported_tool_path


class ToolboxPathValidationTests(unittest.TestCase):
    def test_resolve_supported_tool_path_accepts_existing_exe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tool_file = Path(temp_dir) / "calc.exe"
            tool_file.write_text("binary placeholder", encoding="utf-8")

            resolved = resolve_supported_tool_path(str(tool_file))

            self.assertIsNotNone(resolved)
            self.assertEqual(resolved, tool_file.resolve())

    def test_resolve_supported_tool_path_accepts_existing_generic_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            text_file = Path(temp_dir) / "notes.txt"
            text_file.write_text("hello", encoding="utf-8")

            resolved = resolve_supported_tool_path(str(text_file))

            self.assertIsNotNone(resolved)
            self.assertEqual(resolved, text_file.resolve())

    def test_resolve_supported_tool_path_accepts_existing_pyw(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            script_file = Path(temp_dir) / "convert.pyw"
            script_file.write_text("print('ok')", encoding="utf-8")

            resolved = resolve_supported_tool_path(str(script_file))

            self.assertIsNotNone(resolved)
            self.assertEqual(resolved, script_file.resolve())

    def test_resolve_supported_tool_path_rejects_missing_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing.exe"

            resolved = resolve_supported_tool_path(str(missing))

            self.assertIsNone(resolved)

    def test_resolve_supported_tool_path_accepts_existing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir) / "workspace"
            directory.mkdir()

            resolved = resolve_supported_tool_path(str(directory))

            self.assertIsNotNone(resolved)
            self.assertEqual(resolved, directory.resolve())


if __name__ == "__main__":
    unittest.main()
