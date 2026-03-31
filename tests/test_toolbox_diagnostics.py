import tempfile
import unittest
from pathlib import Path

from app import constants
from app.domain.models import ToolboxEntry, ToolboxTabData
from app.services.diagnostics import find_broken_tool_entries


class ToolboxDiagnosticsTests(unittest.TestCase):
    def test_find_broken_tool_entries_reports_missing_paths(self) -> None:
        tab = ToolboxTabData(
            title="Work",
            tab_id="tab-work",
            entries=[
                ToolboxEntry(
                    title="Missing",
                    kind=constants.ENTRY_KIND_TOOL,
                    path=r"C:\definitely\missing\tool.exe",
                    entry_id="tool-missing",
                )
            ],
        )

        broken = find_broken_tool_entries([tab])

        self.assertEqual(1, len(broken))
        self.assertEqual("tab-work", broken[0].tab_id)
        self.assertEqual("tool-missing", broken[0].entry_id)
        self.assertIn("not found", broken[0].reason.lower())

    def test_find_broken_tool_entries_ignores_valid_tools_and_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            valid_tool = Path(temp_dir) / "ok_tool.cmd"
            valid_tool.write_text("@echo off", encoding="utf-8")
            tab = ToolboxTabData(
                title="Work",
                tab_id="tab-work",
                entries=[
                    ToolboxEntry(
                        title="Valid",
                        kind=constants.ENTRY_KIND_TOOL,
                        path=str(valid_tool),
                        entry_id="tool-valid",
                    ),
                    ToolboxEntry(
                        title="Separator",
                        kind=constants.ENTRY_KIND_SECTION,
                        path="",
                        entry_id="section-1",
                    ),
                ],
            )

            broken = find_broken_tool_entries([tab])

            self.assertEqual([], broken)


if __name__ == "__main__":
    unittest.main()
