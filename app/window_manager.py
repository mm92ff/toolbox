"""Create and coordinate multiple synchronized Toolbox windows."""

from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from app.main_window import MainWindow
from app.services.appimage_icons import AppImageIconService
from app.services.folder_count import FolderCountService
from app.state.settings_controller import SharedSettingsController
from app.state.folder_browse_appearance import FolderBrowseAppearanceStore
from app.state.toolbox_repository import ToolboxStateRepository
from app.tray_controller import ApplicationTrayController


class WindowManager(QtCore.QObject):
    """Application-level owner for windows, shared services, state and tray."""

    def __init__(
        self,
        app_name: str,
        config_dir: Path,
        *,
        icon_path: Path | None = None,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.app_name = app_name
        self.config_dir = Path(config_dir)
        self.icon_path = icon_path
        self.repository = ToolboxStateRepository(self.config_dir, self)
        self.repository.persistence_failed.connect(self._on_persistence_failed)
        self.settings = SharedSettingsController(self)
        self.folder_browse_appearance = FolderBrowseAppearanceStore(self)
        self.folder_count_service = FolderCountService(self, max_workers=2)
        self.appimage_icon_service = AppImageIconService(self)
        self.tray = ApplicationTrayController(self._tray_icon_path(), self)
        self.tray.show_last_requested.connect(self.show_last_window)
        self.tray.new_window_requested.connect(self.create_window)
        self.tray.quit_requested.connect(self.quit)
        self._windows: list[MainWindow] = []
        self._last_active: MainWindow | None = None
        self._shutting_down = False
        self._show_tray_icon = False
        self._minimize_to_tray = False
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.shutdown)

    def _tray_icon_path(self) -> Path | None:
        candidate = Path(__file__).resolve().parent / "assets" / "one_tray.png"
        return candidate if candidate.is_file() else self.icon_path

    @property
    def windows(self) -> tuple[MainWindow, ...]:
        return tuple(self._windows)

    def create_window(self, preferred_tab_id: str | None = None) -> MainWindow:
        window = MainWindow(
            self.app_name,
            config_dir=self.config_dir,
            state_repository=self.repository,
            settings_controller=self.settings,
            folder_browse_appearance_store=self.folder_browse_appearance,
            folder_count_service=self.folder_count_service,
            appimage_icon_service=self.appimage_icon_service,
            managed=True,
        )
        window._window_manager = self
        if self.icon_path is not None:
            window.setWindowIcon(QtGui.QIcon(str(self.icon_path)))
        window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)
        window.new_window_requested.connect(self.create_window)
        window.window_closing.connect(self._remove_window)
        window.installEventFilter(self)
        self._windows.append(window)
        self._last_active = window

        if len(self._windows) > 1:
            previous = self._windows[-2]
            window.move(previous.pos() + QtCore.QPoint(32, 32))
            self._clamp_to_screen(window)
        if preferred_tab_id:
            context = next(
                (ctx for ctx in window.toolbox_tabs if ctx.tab_id == preferred_tab_id), None
            )
            if context is not None:
                window.tab_widget.setCurrentWidget(context.page)
        window.show()
        self.sync_tray_from_window(window)
        return window

    @staticmethod
    def _clamp_to_screen(window: MainWindow) -> None:
        screen = QtGui.QGuiApplication.screenAt(window.frameGeometry().center())
        if screen is None:
            screen = QtGui.QGuiApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        frame = window.frameGeometry()
        x = min(max(frame.x(), area.left()), max(area.left(), area.right() - frame.width()))
        y = min(max(frame.y(), area.top()), max(area.top(), area.bottom() - frame.height()))
        window.move(x, y)

    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if (
            isinstance(watched, MainWindow)
            and event.type() == QtCore.QEvent.Type.WindowActivate
        ):
            self._last_active = watched
        return super().eventFilter(watched, event)

    @QtCore.Slot(str)
    def _remove_window(self, window_id: str) -> None:
        removed = next((w for w in self._windows if w.window_id == window_id), None)
        self._windows = [w for w in self._windows if w.window_id != window_id]
        if self._last_active is removed:
            self._last_active = self._windows[-1] if self._windows else None

    def show_last_window(self) -> MainWindow:
        window = self._last_active
        if window is None or window not in self._windows:
            window = self.create_window()
        window.showNormal()
        window.raise_()
        window.activateWindow()
        self._last_active = window
        return window

    def handle_close_event(
        self, window: MainWindow, event: QtGui.QCloseEvent
    ) -> bool:
        if self._shutting_down or window._force_quit:
            return False
        if len(self._windows) > 1:
            return False
        if self._show_tray_icon and self._minimize_to_tray and self.tray.available:
            event.ignore()
            window.persist_toolbox_state()
            window._save_settings()
            window.hide()
            self.tray.notify_hidden()
            return True
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.setQuitOnLastWindowClosed(True)
        return False

    def sync_tray_from_window(self, window: MainWindow) -> None:
        self._show_tray_icon = bool(window.current_show_tray_icon())
        self._minimize_to_tray = bool(window.current_minimize_to_tray())
        self.tray.set_visible(self._show_tray_icon)
        app = QtWidgets.QApplication.instance()
        if app is not None:
            keep_alive = bool(
                self._show_tray_icon and self._minimize_to_tray and self.tray.available
            )
            app.setQuitOnLastWindowClosed(not keep_alive)

    @QtCore.Slot(str)
    def _on_persistence_failed(self, error: str) -> None:
        message = f"Toolbox state could not be saved: {error}"
        for window in self._windows:
            window.status.showMessage(message, 8000)
        parent = self._last_active if self._last_active in self._windows else None
        QtWidgets.QMessageBox.critical(parent, "Save failed", message)

    def quit(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        for window in list(self._windows):
            window._force_quit = True
            window.close()
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.quit()

    @QtCore.Slot()
    def shutdown(self) -> None:
        if getattr(self, "_shutdown_complete", False):
            return
        self._shutdown_complete = True
        self._shutting_down = True
        self.repository.shutdown()
        self.folder_count_service.shutdown()
        self.appimage_icon_service.shutdown()
        self.tray.icon.hide()
