import os
import shutil
import unittest
import uuid

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtWidgets

from app import constants
from app.main_window import MainWindow


class EntrySectionInsertionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def _create_window(self) -> MainWindow:
        app_name = f"ToolboxStarter_TestSectionInsert_{uuid.uuid4().hex}"
        return MainWindow(app_name)

    def test_add_section_uses_preferred_y_when_provided(self) -> None:
        window = self._create_window()
        try:
            ctx = window.current_toolbox_context()
            self.assertIsNotNone(ctx)
            assert ctx is not None

            preferred_y = 260
            expected_y = ctx.canvas.snap_section_y(ctx.entries, preferred_y)

            original_get_text = QtWidgets.QInputDialog.getText
            QtWidgets.QInputDialog.getText = staticmethod(  # type: ignore[assignment]
                lambda *_args, **_kwargs: ("RightClick Section", True)
            )
            try:
                window.add_section(ctx, preferred_y=preferred_y)
            finally:
                QtWidgets.QInputDialog.getText = original_get_text  # type: ignore[assignment]

            sections = [entry for entry in ctx.entries if entry.kind == constants.ENTRY_KIND_SECTION]
            self.assertEqual(1, len(sections))
            self.assertEqual("RightClick Section", sections[0].title)
            self.assertEqual(constants.CANVAS_PADDING, sections[0].x)
            self.assertEqual(expected_y, sections[0].y)
        finally:
            config_dir = window.config_dir
            window.close()
            shutil.rmtree(config_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
