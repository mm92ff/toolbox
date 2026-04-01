import json
import tempfile
import unittest
from pathlib import Path

from app import constants
from app.domain.models import ToolboxEntry, ToolboxTabData
from app.services.storage import get_tools_file_path, load_toolbox_tabs, save_toolbox_tabs


class ToolboxStorageTests(unittest.TestCase):
    def test_save_and_load_roundtrip_tabs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            tabs = [
                ToolboxTabData(
                    title="Work",
                    tab_id="tab-1",
                    is_primary=True,
                    background_color="#202634",
                    entries=[
                        ToolboxEntry(
                            title="Editor",
                            kind=constants.ENTRY_KIND_TOOL,
                            path=r"C:\Tools\editor.exe",
                            x=40,
                            y=80,
                            always_run_as_admin=True,
                            launch_arguments="--silent",
                            launch_working_directory=r"C:\Tools",
                            launch_wait=True,
                            launch_window_style="minimized",
                            entry_id="entry-1",
                        ),
                        ToolboxEntry(
                            title="Header",
                            kind=constants.ENTRY_KIND_SECTION,
                            x=40,
                            y=220,
                            section_line_color="#ff5500",
                            section_title_color="#ffee00",
                            entry_id="entry-2",
                        ),
                    ],
                )
            ]

            save_toolbox_tabs(config_dir, tabs)
            loaded = load_toolbox_tabs(config_dir)

            self.assertEqual(1, len(loaded))
            self.assertEqual("Work", loaded[0].title)
            self.assertEqual("tab-1", loaded[0].tab_id)
            self.assertTrue(loaded[0].is_primary)
            self.assertEqual("#202634", loaded[0].background_color)
            self.assertEqual(2, len(loaded[0].entries))
            self.assertEqual("entry-1", loaded[0].entries[0].entry_id)
            self.assertTrue(loaded[0].entries[0].always_run_as_admin)
            self.assertEqual("--silent", loaded[0].entries[0].launch_arguments)
            self.assertEqual(r"C:\Tools", loaded[0].entries[0].launch_working_directory)
            self.assertTrue(loaded[0].entries[0].launch_wait)
            self.assertEqual("minimized", loaded[0].entries[0].launch_window_style)
            self.assertEqual("entry-2", loaded[0].entries[1].entry_id)
            self.assertEqual("#ff5500", loaded[0].entries[1].section_line_color)
            self.assertEqual("#ffee00", loaded[0].entries[1].section_title_color)

    def test_load_returns_empty_list_for_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            tools_file = get_tools_file_path(config_dir)
            tools_file.parent.mkdir(parents=True, exist_ok=True)
            tools_file.write_text("{invalid json", encoding="utf-8")

            loaded = load_toolbox_tabs(config_dir)

            self.assertEqual([], loaded)

    def test_load_legacy_entry_list_migrates_to_default_tab(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            tools_file = get_tools_file_path(config_dir)
            tools_file.parent.mkdir(parents=True, exist_ok=True)
            legacy_payload = [
                {
                    "id": "entry-legacy",
                    "title": "Legacy Tool",
                    "kind": constants.ENTRY_KIND_TOOL,
                    "path": r"C:\Tools\legacy.exe",
                }
            ]
            tools_file.write_text(json.dumps(legacy_payload), encoding="utf-8")

            loaded = load_toolbox_tabs(config_dir)

            self.assertEqual(1, len(loaded))
            self.assertEqual(constants.DEFAULT_TOOLBOX_TAB_TITLE, loaded[0].title)
            self.assertFalse(loaded[0].is_primary)
            self.assertEqual(1, len(loaded[0].entries))
            self.assertEqual("entry-legacy", loaded[0].entries[0].entry_id)


if __name__ == "__main__":
    unittest.main()
