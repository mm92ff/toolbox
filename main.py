#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entry point for the toolbox desktop application."""

import json
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

from PySide6 import QtCore, QtGui, QtWidgets

from app import constants
from app.application_controller import (
    InstanceStartResult,
    SingleInstanceController,
    single_instance_server_name,
)
from app.main_window import MainWindow
from app.services.system_utils import get_config_directory
from app.services.linux_icon_theme import initialize_linux_icon_theme

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
    """Return the stable product name independently of the executable filename."""
    return constants.PRODUCT_NAME


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


def _write_smoke_test_report(
    app: QtWidgets.QApplication,
    window: MainWindow,
    config_dir: Path,
    icon_path: Path | None,
) -> None:
    """Write opt-in runtime evidence used by AppDir/AppImage acceptance tests."""
    report_path = os.environ.get("TOOLBOX_SMOKE_REPORT", "").strip()
    if not report_path:
        return

    report = {
        "application_name": app.applicationName(),
        "arguments": sys.argv[1:],
        "config_directory": str(config_dir),
        "desktop_file_name": app.desktopFileName(),
        "device_pixel_ratio": window.devicePixelRatioF(),
        "frozen": bool(getattr(sys, "frozen", False)),
        "icon_available": bool(icon_path is not None and not window.windowIcon().isNull()),
        "icon_theme_name": QtGui.QIcon.themeName(),
        "icon_theme_search_path_count": len(QtGui.QIcon.themeSearchPaths()),
        "organization_name": app.organizationName(),
        "qt_platform": app.platformName(),
        "window_title": window.windowTitle(),
    }
    desktop_fixture = os.environ.get("TOOLBOX_SMOKE_DESKTOP_ENTRY", "").strip()
    if desktop_fixture:
        from app.services.desktop_entries import (
            DesktopLaunchInput,
            desktop_entry_file_field_code,
            read_desktop_entry,
        )
        from app.services.desktop_entry_launch import prepare_desktop_launch
        from app.services.linux_icon_theme import desktop_icon_for_path

        drop_path = os.environ.get("TOOLBOX_SMOKE_DROP_PATH", "").strip()
        launch_input = (
            DesktopLaunchInput.from_local_paths((drop_path,))
            if drop_path
            else DesktopLaunchInput()
        )
        metadata = read_desktop_entry(desktop_fixture, locale_name="de_CH")
        prepared = prepare_desktop_launch(
            desktop_fixture,
            launch_input=launch_input,
        )
        fixture_icon = desktop_icon_for_path(
            desktop_fixture,
            window.icon_provider,
        )
        report.update(
            {
                "desktop_fixture_command": list(prepared.commands[0]),
                "desktop_fixture_field_code": desktop_entry_file_field_code(metadata),
                "desktop_fixture_icon_available": not fixture_icon.isNull(),
                "desktop_fixture_mode": prepared.mode,
                "desktop_fixture_name": metadata.name,
            }
        )
    appimage_fixture = os.environ.get("TOOLBOX_SMOKE_APPIMAGE_ICON", "").strip()
    if appimage_fixture:
        normalized_fixture = os.path.abspath(os.path.expanduser(appimage_fixture))
        extracted_icon_path = ""
        loop = QtCore.QEventLoop()

        def collect_appimage_icon(result_path: str, icon_result: str) -> None:
            nonlocal extracted_icon_path
            if os.path.abspath(os.path.expanduser(result_path)) != normalized_fixture:
                return
            extracted_icon_path = icon_result
            loop.quit()

        window._appimage_icon_service.result_ready.connect(collect_appimage_icon)
        timeout = QtCore.QTimer()
        timeout.setSingleShot(True)
        timeout.timeout.connect(loop.quit)
        timeout.start(6000)
        window._appimage_icon_service.request(normalized_fixture)
        loop.exec()
        window._appimage_icon_service.result_ready.disconnect(collect_appimage_icon)
        extracted_icon = QtGui.QIcon(extracted_icon_path)
        report.update(
            {
                "appimage_fixture_icon_available": bool(
                    extracted_icon_path and not extracted_icon.isNull()
                ),
                "appimage_fixture_icon_is_png": extracted_icon_path.endswith(".png"),
            }
        )
    screenshot_path = os.environ.get("TOOLBOX_SMOKE_SCREENSHOT", "").strip()
    if screenshot_path:
        if (
            os.environ.get("TOOLBOX_SMOKE_TOOLBOX_TAB", "").strip() == "1"
            and window.toolbox_tabs
        ):
            window.tab_widget.setCurrentWidget(window.toolbox_tabs[0].page)
            QtWidgets.QApplication.processEvents()
        screenshot_saved = window.grab().save(screenshot_path, "PNG")
        report["screenshot_saved"] = bool(screenshot_saved)
    Path(report_path).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    """Start the application and return the process exit code."""
    configure_logging()
    install_exception_hook()
    app_name = get_app_name()
    app = QtWidgets.QApplication(sys.argv)
    if sys.platform.startswith("linux"):
        initialize_linux_icon_theme()
    app.setOrganizationName(constants.ORGANIZATION_NAME)
    app.setApplicationName(constants.PRODUCT_NAME)
    if sys.platform.startswith("linux"):
        app.setDesktopFileName(constants.DESKTOP_FILE_NAME)
    icon_path = _resolve_app_icon_path()
    if icon_path is not None:
        app.setWindowIcon(QtGui.QIcon(str(icon_path)))

    try:
        config_dir = get_config_directory(constants.CONFIG_DIRECTORY_NAME)
    except OSError as exc:
        logger.error("Startup aborted: configuration directory unavailable: %s", exc)
        QtWidgets.QMessageBox.critical(
            None,
            "Startup Error",
            f"Configuration directory is unavailable.\n{exc}",
        )
        return 1

    smoke_test_requested = (
        "--smoke-test" in sys.argv
        or os.environ.get("TOOLBOX_SMOKE_TEST", "").strip() == "1"
    )
    instance_controller = None

    if not smoke_test_requested:
        instance_suffix = os.environ.get("TOOLBOX_INSTANCE_KEY", "").strip()
        instance_controller = SingleInstanceController(
            single_instance_server_name(instance_suffix),
            app,
        )
        instance_result = instance_controller.start()
        if instance_result is InstanceStartResult.SECONDARY:
            return 0
        if instance_result is InstanceStartResult.FAILED:
            return 1

    window = MainWindow(app_name, config_dir=config_dir)
    if icon_path is not None:
        window.setWindowIcon(QtGui.QIcon(str(icon_path)))
    window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose)

    if instance_controller is not None:
        instance_controller.activation_requested.connect(window._show_from_tray)

    window.show()
    if smoke_test_requested:
        app.processEvents()
        _write_smoke_test_report(app, window, config_dir, icon_path)
        window._force_quit = True
        window.close()
        app.processEvents()
        return 0
    return app.exec()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user.")
        sys.exit(130)
