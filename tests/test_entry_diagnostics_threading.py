import os
import shutil
import time
import unittest
import uuid

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets

from app.main_window import MainWindow


class EntryDiagnosticsThreadingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def _create_window(self) -> MainWindow:
        app_name = f"ToolboxStarter_TestDiagnosticsThreading_{uuid.uuid4().hex}"
        return MainWindow(app_name)

    def test_broken_entries_result_handler_runs_on_ui_thread(self) -> None:
        window = self._create_window()
        try:
            called = False
            called_on_ui_thread = False
            ui_thread = self.app.thread()

            def patched_show(_broken_entries: object) -> None:
                nonlocal called, called_on_ui_thread
                called = True
                called_on_ui_thread = QtCore.QThread.currentThread() is ui_thread

            window._show_broken_entries_dialog = patched_show  # type: ignore[method-assign]
            window._run_broken_entries_check()

            timeout_s = 6.0
            start = time.perf_counter()
            while getattr(window, "_broken_entries_scan_thread", None) is not None:
                self.app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 50)
                time.sleep(0.01)
                if time.perf_counter() - start > timeout_s:
                    break

            self.assertTrue(called, "Diagnostics result handler was not called.")
            self.assertTrue(
                called_on_ui_thread,
                "Diagnostics dialog handler did not execute on the UI thread.",
            )
            self.assertIsNone(getattr(window, "_broken_entries_scan_thread", None))
        finally:
            config_dir = window.config_dir
            window.close()
            shutil.rmtree(config_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
