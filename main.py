#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entry point for the toolbox desktop application."""

import logging
import os
import sys
from pathlib import Path
from types import TracebackType

# Ensure proper encoding for console output on Windows
if sys.platform == "win32":
    import codecs

    if getattr(sys.stdout, "buffer", None) is not None:
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    if getattr(sys.stderr, "buffer", None) is not None:
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

from PySide6 import QtGui, QtWidgets

from app import constants
from app.main_window import MainWindow
from app.services.system_utils import get_config_directory

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    """Configure default application logging for startup/runtime failures."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def log_unhandled_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
) -> None:
    """Log uncaught exceptions with traceback before process termination."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.critical(
        "Unhandled exception in top-level application flow.",
        exc_info=(exc_type, exc_value, exc_traceback),
    )


def install_exception_hook() -> None:
    """Install application-wide uncaught-exception logging hook."""
    sys.excepthook = log_unhandled_exception


def get_app_name() -> str:
    """Determines the application name from the filename."""
    app_filename = os.path.basename(sys.argv[0]) if sys.argv else ""
    app_name = os.path.splitext(app_filename)[0].strip()
    return app_name or constants.DEFAULT_APP_NAME


def _resolve_app_icon_path() -> Path | None:
    """Resolve the packaged/development path to the application icon."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        packaged = Path(meipass) / "app" / "assets" / "one.png"
        if packaged.is_file():
            return packaged
    candidate = Path(__file__).resolve().parent / "app" / "assets" / "one.png"
    if candidate.is_file():
        return candidate
    return None


def main() -> int:
    """Start the application and return the process exit code."""
    configure_logging()
    install_exception_hook()
    app_name = get_app_name()
    app = QtWidgets.QApplication(sys.argv)
    app.setOrganizationName(app_name)
    app.setApplicationName(app_name)
    icon_path = _resolve_app_icon_path()
    if icon_path is not None:
        app.setWindowIcon(QtGui.QIcon(str(icon_path)))

    try:
        config_dir = get_config_directory(app_name)
    except OSError as exc:
        logger.error("Startup aborted: configuration directory unavailable: %s", exc)
        QtWidgets.QMessageBox.critical(
            None,
            "Startup Error",
            f"Configuration directory is unavailable.\n{exc}",
        )
        return 1

    window = MainWindow(app_name, config_dir=config_dir)
    if icon_path is not None:
        window.setWindowIcon(QtGui.QIcon(str(icon_path)))
    window.show()
    return app.exec()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user.")
        sys.exit(130)
