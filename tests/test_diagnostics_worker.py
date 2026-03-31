import unittest

from app.domain.models import ToolboxEntry, ToolboxTabData
from app.features.entries.diagnostics_worker import clone_tab_snapshots, coerce_broken_entries
from app.services.diagnostics import BrokenToolEntry


class DiagnosticsWorkerHelperTests(unittest.TestCase):
    def test_clone_tab_snapshots_returns_detached_list(self) -> None:
        source_tabs = [
            ToolboxTabData(
                title="Work",
                tab_id="tab-1",
                is_primary=True,
                entries=[
                    ToolboxEntry(
                        title="Editor",
                        kind="tool",
                        path=r"C:\Tools\editor.exe",
                        entry_id="entry-1",
                    )
                ],
            )
        ]

        cloned = clone_tab_snapshots(source_tabs)
        self.assertEqual(1, len(cloned))
        self.assertIsNot(cloned[0], source_tabs[0])
        self.assertEqual("Work", cloned[0].title)
        self.assertEqual(1, len(cloned[0].entries))

    def test_coerce_broken_entries_accepts_valid_payload(self) -> None:
        payload = [
            BrokenToolEntry(
                tab_id="tab-1",
                tab_title="Work",
                entry_id="entry-1",
                entry_title="Editor",
                path=r"C:\Tools\editor.exe",
                reason="missing",
            )
        ]
        self.assertEqual(payload, coerce_broken_entries(payload))

    def test_coerce_broken_entries_rejects_non_matching_payload(self) -> None:
        self.assertEqual([], coerce_broken_entries("invalid"))
        self.assertEqual([], coerce_broken_entries([{"entry_id": "x"}]))


if __name__ == "__main__":
    unittest.main()
