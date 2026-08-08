"""One system-tray icon owned by the application rather than a window."""

from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets


class ApplicationTrayController(QtCore.QObject):
    show_last_requested = QtCore.Signal()
    new_window_requested = QtCore.Signal()
    quit_requested = QtCore.Signal()

    def __init__(
        self,
        icon_path: Path | None = None,
        parent: QtCore.QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.icon = QtWidgets.QSystemTrayIcon(self)
        icon = QtGui.QIcon(str(icon_path)) if icon_path is not None else QtGui.QIcon()
        if icon.isNull():
            app = QtWidgets.QApplication.instance()
            icon = app.windowIcon() if app is not None else QtGui.QIcon()
        if icon.isNull():
            icon = QtGui.QIcon.fromTheme("applications-system")
        pixmap = icon.pixmap(64, 64)
        self.icon.setIcon(QtGui.QIcon(pixmap) if not pixmap.isNull() else icon)

        self.menu = QtWidgets.QMenu()
        self.menu.addAction("Show Last Window", self.show_last_requested.emit)
        self.menu.addAction("New Window", self.new_window_requested.emit)
        self.menu.addSeparator()
        self.menu.addAction("Quit Toolbox", self.quit_requested.emit)
        self.icon.setContextMenu(self.menu)
        self.icon.activated.connect(self._activated)

    @property
    def available(self) -> bool:
        return QtWidgets.QSystemTrayIcon.isSystemTrayAvailable()

    def set_visible(self, visible: bool) -> None:
        self.icon.setVisible(bool(visible and self.available))

    def notify_hidden(self) -> None:
        self.icon.showMessage(
            "Toolbox läuft im Hintergrund",
            "Die Toolbox wurde in den Tray minimiert.",
            QtWidgets.QSystemTrayIcon.MessageIcon.Information,
            2000,
        )

    def _activated(self, reason: QtWidgets.QSystemTrayIcon.ActivationReason) -> None:
        if reason == QtWidgets.QSystemTrayIcon.ActivationReason.Trigger:
            self.show_last_requested.emit()
