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
    resolve_second_launch_command,
    single_instance_server_name,
)
from app.main_window import MainWindow
from app.window_manager import WindowManager
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
    toolbox_context = window.toolbox_tabs[0] if window.toolbox_tabs else None
    folder_size_slider = (
        toolbox_context.browse_icon_size_slider
        if toolbox_context is not None
        else None
    )
    folder_size_reset = (
        toolbox_context.browse_icon_size_reset_button
        if toolbox_context is not None
        else None
    )
    report.update(
        {
            "responsive_layout_setting_available": (
                constants.WIDGET_RESPONSIVE_TOOLBOX_LAYOUT_CHECKBOX in window.widgets
            ),
            "responsive_layout_setting_enabled": window.current_responsive_toolbox_layout(),
            "responsive_layout_normal_canvas_enabled": bool(
                toolbox_context is not None
                and toolbox_context.canvas.responsive_layout_enabled()
            ),
            "folder_icon_size_slider_available": folder_size_slider is not None,
            "folder_icon_size_slider_minimum": (
                folder_size_slider.minimum() if folder_size_slider is not None else None
            ),
            "folder_icon_size_slider_maximum": (
                folder_size_slider.maximum() if folder_size_slider is not None else None
            ),
            "folder_icon_size_reset_available": folder_size_reset is not None,
        }
    )
    folder_appearance_fixture = os.environ.get(
        "TOOLBOX_SMOKE_FOLDER_APPEARANCE_PATH", ""
    ).strip()
    if folder_appearance_fixture and toolbox_context is not None:
        fixture_path = Path(folder_appearance_fixture).expanduser().resolve(strict=False)
        window._enter_folder_browse(toolbox_context, fixture_path)
        requested_size = os.environ.get(
            "TOOLBOX_SMOKE_FOLDER_ICON_SIZE", ""
        ).strip()
        if requested_size and toolbox_context.browse_icon_size_slider is not None:
            toolbox_context.browse_icon_size_slider.setValue(int(requested_size))
            window._commit_folder_icon_size_change(toolbox_context)
        app.processEvents()
        original_viewport_width = toolbox_context.canvas.viewport().width()
        toolbox_context.canvas.surface.set_viewport_width(900)
        responsive_wide_columns = toolbox_context.canvas.responsive_columns()
        toolbox_context.canvas.surface.set_viewport_width(220)
        responsive_narrow_columns = toolbox_context.canvas.responsive_columns()
        toolbox_context.canvas.surface.set_viewport_width(original_viewport_width)
        report.update(
            {
                "folder_icon_size_browse_visible": bool(
                    toolbox_context.breadcrumb_bar is not None
                    and toolbox_context.breadcrumb_bar.isVisible()
                ),
                "folder_icon_size_effective": (
                    toolbox_context.browse_icon_size_slider.value()
                    if toolbox_context.browse_icon_size_slider is not None
                    else None
                ),
                "folder_icon_size_override": (
                    window._folder_browse_appearance_store.get_override(fixture_path)
                ),
                "responsive_layout_browse_canvas_enabled": (
                    toolbox_context.canvas.responsive_layout_enabled()
                ),
                "responsive_layout_browse_columns": (
                    toolbox_context.canvas.responsive_columns()
                ),
                "responsive_layout_browse_wide_columns": responsive_wide_columns,
                "responsive_layout_browse_narrow_columns": responsive_narrow_columns,
            }
        )
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


def _install_x11_responsive_probe(window: MainWindow, report_path: str) -> None:
    """Expose responsive state for the opt-in real-X11 release acceptance test."""

    from app.domain.models import ToolboxEntry

    ctx = window.current_toolbox_context()
    if ctx is None:
        return
    probe_entries = [
        ToolboxEntry(
            title=f"Responsive probe {index}",
            path=f"/tmp/toolbox-responsive-probe-{index}",
            x=constants.CANVAS_PADDING + index,
            y=constants.CANVAS_PADDING,
            entry_id=f"responsive-probe-{index}",
        )
        for index in range(12)
    ]
    ctx.entries.extend(probe_entries)
    canonical_positions = {
        entry.entry_id: (entry.x, entry.y) for entry in probe_entries
    }
    window._applied_responsive_toolbox_layout = True
    window.refresh_canvas(ctx)

    target = Path(report_path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)

    def write_probe_report() -> None:
        current_positions = {
            entry.entry_id: (entry.x, entry.y) for entry in probe_entries
        }
        payload = {
            "canonical_unchanged": current_positions == canonical_positions,
            "columns": ctx.canvas.responsive_columns(),
            "responsive_enabled": ctx.canvas.responsive_layout_enabled(),
            "viewport_width": ctx.canvas.viewport().width(),
            "window_width": window.width(),
        }
        temporary = target.with_name(f".{target.name}.tmp")
        temporary.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, target)

    timer = QtCore.QTimer(window)
    timer.setInterval(40)
    timer.timeout.connect(write_probe_report)
    timer.start()
    window._x11_responsive_probe_timer = timer
    write_probe_report()


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
        second_launch_action = QtCore.QSettings().value(
            "system/second_launch_action",
            constants.DEFAULT_SECOND_LAUNCH_ACTION,
            type=str,
        )
        ipc_command = resolve_second_launch_command(
            sys.argv[1:], second_launch_action
        )
        instance_result = instance_controller.start(ipc_command)
        if instance_result is InstanceStartResult.SECONDARY:
            return 0
        if instance_result is InstanceStartResult.FAILED:
            return 1

    window_manager = WindowManager(
        app_name,
        config_dir,
        icon_path=icon_path,
        parent=app,
    )
    window = window_manager.create_window()

    x11_probe_report = os.environ.get("TOOLBOX_X11_RESPONSIVE_REPORT", "").strip()
    if x11_probe_report:
        _install_x11_responsive_probe(window, x11_probe_report)

    if instance_controller is not None:
        instance_controller.command_received.connect(
            lambda command, _payload: (
                window_manager.create_window()
                if command == "new_window"
                else window_manager.show_last_window()
            )
        )

    if smoke_test_requested:
        app.processEvents()
        _write_smoke_test_report(app, window, config_dir, icon_path)
        window_manager.quit()
        app.processEvents()
        return 0
    return app.exec()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user.")
        sys.exit(130)
