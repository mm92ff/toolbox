import os
import shutil
import unittest
import uuid

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets

from app import constants
from app.main_window import MainWindow


class UndoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def _create_window(self) -> MainWindow:
        app_name = f"ToolboxStarter_TestUndo_{uuid.uuid4().hex}"
        return MainWindow(app_name)

    def test_undo_restores_previous_toolbox_state(self) -> None:
        window = self._create_window()
        try:
            ctx = window.current_toolbox_context()
            self.assertIsNotNone(ctx)
            assert ctx is not None
            self.assertEqual(0, len(ctx.entries))

            original_get_text = QtWidgets.QInputDialog.getText
            QtWidgets.QInputDialog.getText = staticmethod(  # type: ignore[assignment]
                lambda *_args, **_kwargs: ("Header Undo", True)
            )
            try:
                window.add_section(ctx)
            finally:
                QtWidgets.QInputDialog.getText = original_get_text  # type: ignore[assignment]

            self.assertEqual(1, len(ctx.entries))
            self.assertEqual(constants.ENTRY_KIND_SECTION, ctx.entries[0].kind)

            window._undo_last_toolbox_change()
            self.assertEqual(0, len(window.toolbox_tabs[0].entries))
        finally:
            config_dir = window.config_dir
            window.close()
            shutil.rmtree(config_dir, ignore_errors=True)

    def test_ctrl_z_triggers_undo(self) -> None:
        window = self._create_window()
        try:
            ctx = window.current_toolbox_context()
            self.assertIsNotNone(ctx)
            assert ctx is not None

            original_get_text = QtWidgets.QInputDialog.getText
            QtWidgets.QInputDialog.getText = staticmethod(  # type: ignore[assignment]
                lambda *_args, **_kwargs: ("Header CtrlZ", True)
            )
            try:
                window.add_section(ctx)
            finally:
                QtWidgets.QInputDialog.getText = original_get_text  # type: ignore[assignment]

            self.assertEqual(1, len(ctx.entries))
            event = QtGui.QKeyEvent(
                QtCore.QEvent.Type.KeyPress,
                QtCore.Qt.Key.Key_Z,
                QtCore.Qt.KeyboardModifier.ControlModifier,
            )
            window.keyPressEvent(event)

            self.assertEqual(0, len(window.toolbox_tabs[0].entries))
        finally:
            config_dir = window.config_dir
            window.close()
            shutil.rmtree(config_dir, ignore_errors=True)

    def test_redo_restores_undone_change(self) -> None:
        window = self._create_window()
        try:
            ctx = window.current_toolbox_context()
            self.assertIsNotNone(ctx)
            assert ctx is not None

            original_get_text = QtWidgets.QInputDialog.getText
            QtWidgets.QInputDialog.getText = staticmethod(  # type: ignore[assignment]
                lambda *_args, **_kwargs: ("Header Redo", True)
            )
            try:
                window.add_section(ctx)
            finally:
                QtWidgets.QInputDialog.getText = original_get_text  # type: ignore[assignment]

            self.assertEqual(1, len(window.toolbox_tabs[0].entries))
            window._undo_last_toolbox_change()
            self.assertEqual(0, len(window.toolbox_tabs[0].entries))

            window._redo_last_toolbox_change()
            self.assertEqual(1, len(window.toolbox_tabs[0].entries))
        finally:
            config_dir = window.config_dir
            window.close()
            shutil.rmtree(config_dir, ignore_errors=True)

    def test_ctrl_y_triggers_redo(self) -> None:
        window = self._create_window()
        try:
            ctx = window.current_toolbox_context()
            self.assertIsNotNone(ctx)
            assert ctx is not None

            original_get_text = QtWidgets.QInputDialog.getText
            QtWidgets.QInputDialog.getText = staticmethod(  # type: ignore[assignment]
                lambda *_args, **_kwargs: ("Header CtrlY", True)
            )
            try:
                window.add_section(ctx)
            finally:
                QtWidgets.QInputDialog.getText = original_get_text  # type: ignore[assignment]

            window._undo_last_toolbox_change()
            self.assertEqual(0, len(window.toolbox_tabs[0].entries))

            event = QtGui.QKeyEvent(
                QtCore.QEvent.Type.KeyPress,
                QtCore.Qt.Key.Key_Y,
                QtCore.Qt.KeyboardModifier.ControlModifier,
            )
            window.keyPressEvent(event)
            self.assertEqual(1, len(window.toolbox_tabs[0].entries))
        finally:
            config_dir = window.config_dir
            window.close()
            shutil.rmtree(config_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
