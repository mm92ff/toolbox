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

    def test_find_broken_tool_entries_reports_invalid_desktop_exec(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            desktop = Path(temp_dir) / "Broken.desktop"
            desktop.write_text(
                (
                    "[Desktop Entry]\n"
                    "Type=Application\n"
                    "Name=Broken\n"
                    "Exec=definitely-missing-toolbox-command\n"
                ),
                encoding="utf-8",
            )
            tab = ToolboxTabData(
                title="Linux",
                entries=[
                    ToolboxEntry(
                        title="Broken Desktop",
                        path=str(desktop),
                    )
                ],
            )

            broken = find_broken_tool_entries([tab])

            self.assertEqual(1, len(broken))
            self.assertIn("not found", broken[0].reason.lower())

    def test_find_broken_tool_entries_accepts_valid_desktop_exec(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            desktop = Path(temp_dir) / "Valid.desktop"
            desktop.write_text(
                (
                    "[Desktop Entry]\n"
                    "Type=Application\n"
                    "Name=Valid\n"
                    "Exec=/usr/bin/true\n"
                ),
                encoding="utf-8",
            )
            tab = ToolboxTabData(
                title="Linux",
                entries=[ToolboxEntry(title="Valid Desktop", path=str(desktop))],
            )

            self.assertEqual([], find_broken_tool_entries([tab]))

    def test_desktop_diagnostics_distinguish_missing_exec_and_try_exec(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            missing_exec = root / "MissingExec.desktop"
            missing_exec.write_text(
                "[Desktop Entry]\nType=Application\nName=Missing Exec\n",
                encoding="utf-8",
            )
            missing_try_exec = root / "MissingTryExec.desktop"
            missing_try_exec.write_text(
                (
                    "[Desktop Entry]\n"
                    "Type=Application\n"
                    "Name=Missing TryExec\n"
                    "Exec=/usr/bin/true\n"
                    "TryExec=definitely-missing-toolbox-command\n"
                ),
                encoding="utf-8",
            )
            tab = ToolboxTabData(
                title="Linux",
                entries=[
                    ToolboxEntry(title="Missing Exec", path=str(missing_exec)),
                    ToolboxEntry(title="Missing TryExec", path=str(missing_try_exec)),
                ],
            )

            broken = find_broken_tool_entries([tab])
            reasons = {item.entry_title: item.reason for item in broken}

            self.assertIn("missing Exec", reasons["Missing Exec"])
            self.assertIn("not found", reasons["Missing TryExec"])

    def test_missing_desktop_icon_is_valid_and_uses_ui_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            desktop = Path(temp_dir) / "NoIcon.desktop"
            desktop.write_text(
                (
                    "[Desktop Entry]\n"
                    "Type=Application\n"
                    "Name=No Icon\n"
                    "Exec=/usr/bin/true\n"
                ),
                encoding="utf-8",
            )
            tab = ToolboxTabData(
                title="Linux",
                entries=[ToolboxEntry(title="No Icon", path=str(desktop))],
            )

            self.assertEqual([], find_broken_tool_entries([tab]))


if __name__ == "__main__":
    unittest.main()
