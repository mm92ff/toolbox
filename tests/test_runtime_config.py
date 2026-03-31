import tempfile
import unittest
from pathlib import Path

from app.services.system_utils import ensure_writable_directory


class RuntimeConfigValidationTests(unittest.TestCase):
    def test_ensure_writable_directory_creates_missing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "config"

            ensure_writable_directory(config_dir)

            self.assertTrue(config_dir.exists())
            self.assertTrue(config_dir.is_dir())

    def test_ensure_writable_directory_rejects_file_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            not_a_dir = Path(temp_dir) / "config"
            not_a_dir.write_text("not-a-directory", encoding="utf-8")

            with self.assertRaises(OSError):
                ensure_writable_directory(not_a_dir)


if __name__ == "__main__":
    unittest.main()
