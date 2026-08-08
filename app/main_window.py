#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Main window orchestration for the toolbox launcher."""

from __future__ import annotations

import sys
import uuid
import weakref
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from app import constants
from app.domain.tab_context import ToolboxTabContext
from app.features.entries.controller import MainWindowEntriesMixin
from app.features.settings.controller import MainWindowSettingsMixin
from app.features.tabs.controller import MainWindowTabsMixin
from app.services.appimage_icons import AppImageIconService
from app.services.desktop_entry_launch import DesktopProcessManager
from app.services.folder_count import FolderCountService
from app.services.size_calculator import TabSizeCalculationService
from app.services.system_utils import get_config_directory
from app.state.folder_browse_appearance import FolderBrowseAppearanceStore
from app.ui.layouts import UIBuilder


class MainWindow(
    MainWindowEntriesMixin,
    MainWindowSettingsMixin,
    MainWindowTabsMixin,
    QtWidgets.QMainWindow,
):
    """Main application window for the EXE/shortcut toolbox."""

    new_window_requested = QtCore.Signal()
    window_closing = QtCore.Signal(str)

    def __init__(
        self,
        app_name: str,
        config_dir: Path | None = None,
        *,
        state_repository: object | None = None,
        settings_controller: object | None = None,
        folder_browse_appearance_store: FolderBrowseAppearanceStore | None = None,
        folder_count_service: FolderCountService | None = None,
        appimage_icon_service: AppImageIconService | None = None,
        managed: bool = False,
        window_id: str | None = None,
    ):
        super().__init__()
        self.window_id = window_id or uuid.uuid4().hex
        self._managed = bool(managed)
        self._state_repository = state_repository
        self._shared_state_revision = 0
        self._settings_controller = settings_controller
        self._folder_browse_appearance_store = (
            folder_browse_appearance_store
            if folder_browse_appearance_store is not None
            else FolderBrowseAppearanceStore(self)
        )
        self._shared_settings_conflict = False
        self._shared_settings_revision = 0
        self._owns_shared_services = (
            folder_count_service is None and appimage_icon_service is None
        )
        self.app_name = app_name or constants.DEFAULT_APP_NAME
        self.setWindowTitle(self.app_name)
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.setOrganizationName(self.app_name)
            app.setApplicationName(self.app_name)

        self.config_dir = (
            config_dir if config_dir is not None else get_config_directory(self.app_name)
        )
        self.icon_provider = QtWidgets.QFileIconProvider()
        self.desktop_process_manager = DesktopProcessManager(self)
        self.desktop_process_manager.launch_started.connect(
            self._on_desktop_launch_started
        )
        self.desktop_process_manager.launch_delegated.connect(
            self._on_desktop_launch_delegated
        )
        self.desktop_process_manager.launch_finished.connect(
            self._on_desktop_launch_finished
        )
        self.desktop_process_manager.launch_failed.connect(
            self._on_desktop_launch_failed
        )
        self.toolbox_tabs: list[ToolboxTabContext] = []
        self._drop_widget_map: weakref.WeakKeyDictionary[QtCore.QObject, ToolboxTabContext] = (
            weakref.WeakKeyDictionary()
        )
        self._settings_title = "Settings"
        self._help_title = "Help"
        self._pending_current_tab_index = 0
        self._settings_ready = False
        self._settings_dirty = False
        self._hidden_toolbox_tab_ids: set[str] = set()
        self._help_tab_hidden = False
        self._updating_tab_manager = False
        self._auto_applying_settings_on_tab_change = False
        self._last_tab_index = 0
        self._undo_stack: list[list[dict[str, object]]] = []
        self._redo_stack: list[list[dict[str, object]]] = []
        self._undo_last_state: list[dict[str, object]] | None = None
        self._undo_suspended = False
        self._undo_max_steps = 50
        self._show_tray_icon = constants.DEFAULT_SHOW_TRAY_ICON
        self._minimize_to_tray = constants.DEFAULT_MINIMIZE_TO_TRAY
        self._force_quit = False
        self.tray_icon: QtWidgets.QSystemTrayIcon | None = None
        self._closing = False
        self._shutdown_complete = False
        self._pending_size_request: tuple[str, tuple[str, ...]] | None = None
        self._last_size_signatures: dict[str, tuple[str, ...]] = {}
        self._size_service = TabSizeCalculationService(self)
        self._size_service.result_ready.connect(self._on_tab_size_calculated)
        self._folder_count_service = folder_count_service or FolderCountService(
            self, max_workers=2
        )
        self._appimage_icon_service = appimage_icon_service or AppImageIconService(self)
        self._size_recalc_timer = QtCore.QTimer(self)
        self._size_recalc_timer.setSingleShot(True)
        self._size_recalc_timer.setInterval(180)
        self._size_recalc_timer.timeout.connect(self._start_pending_tab_size_calculation)
        self._initialize_applied_settings_defaults()

        self.status = self.statusBar()
        self.status.showMessage("Ready")

        self._setup_ui()
        if app is not None and not self._managed:
            app.aboutToQuit.connect(self._persist_on_quit)
        self._load_toolbox_state()
        self._load_settings()
        self.refresh_all_canvases()
        self._initialize_undo_history()
        self._settings_ready = True

        if self._state_repository is not None:
            self._shared_state_revision = self._state_repository.revision
            self._state_repository.state_changed.connect(
                self._on_shared_toolbox_state_changed
            )
        if self._settings_controller is not None:
            self._shared_settings_revision = self._settings_controller.revision
            self._settings_controller.settings_changed.connect(
                self._on_shared_settings_changed
            )
        self._folder_browse_appearance_store.icon_size_changed.connect(
            self._on_folder_browse_appearance_changed
        )

        ctx = self.current_toolbox_context()
        if ctx is not None:
            self._schedule_active_tab_size(ctx, force=True)

    def _update_window_minimum_width(self, ctx: ToolboxTabContext) -> None:
        del ctx
        self.setMinimumWidth(self.minimumSizeHint().width())

    def _update_managed_window_title(self) -> None:
        if not self._managed:
            return
        ctx = self.current_toolbox_context()
        self.setWindowTitle(
            f"{self.app_name} — {ctx.title}" if ctx is not None else self.app_name
        )

    def _on_shared_settings_changed(
        self, origin_window_id: str, revision: int, _snapshot: object
    ) -> None:
        if origin_window_id == self.window_id:
            self._shared_settings_revision = revision
            self._shared_settings_conflict = False
            return
        if self._settings_dirty:
            self._shared_settings_conflict = True
            self.status.showMessage(
                "Settings changed in another window. Reload before applying.", 5000
            )
            return
        self._shared_settings_revision = revision
        self._reload_shared_settings()

    def _reload_shared_settings(self) -> None:
        geometry = self.saveGeometry()
        current = self.current_toolbox_context()
        current_tab_id = current.tab_id if current is not None else None
        self._load_settings()
        self.restoreGeometry(geometry)
        if current_tab_id is not None:
            restored = next(
                (ctx for ctx in self.toolbox_tabs if ctx.tab_id == current_tab_id), None
            )
            if restored is not None:
                self.tab_widget.setCurrentWidget(restored.page)
        self.refresh_all_canvases(apply_layout_only=True)
        self._shared_settings_conflict = False

    def _schedule_active_tab_size(self, ctx: ToolboxTabContext, force: bool = False) -> None:
        if self._closing:
            return
        paths = tuple(sorted(entry.path for entry in ctx.entries if entry.is_tool and entry.path))
        if not force and self._last_size_signatures.get(ctx.tab_id) == paths:
            return
        self._pending_size_request = (ctx.tab_id, paths)
        self.tab_size_label.setText("Berechne Tab-Größe...")
        self._size_recalc_timer.start()

    def _recalculate_active_tab_size(self, ctx: ToolboxTabContext) -> None:
        self._schedule_active_tab_size(ctx, force=True)

    def _start_pending_tab_size_calculation(self) -> None:
        request = self._pending_size_request
        self._pending_size_request = None
        if self._closing or request is None:
            return
        tab_id, paths = request
        self._last_size_signatures[tab_id] = paths
        self._size_service.request(tab_id, paths)

    def _on_tab_size_calculated(self, tab_id: str, result: str) -> None:
        ctx = self.current_toolbox_context()
        if not self._closing and ctx is not None and ctx.tab_id == tab_id:
            self.tab_size_label.setText(f"Gesamtgröße: {result}")

    def _persist_on_quit(self) -> None:
        self._begin_shutdown()

    def _begin_shutdown(self) -> None:
        if self._shutdown_complete:
            return
        self._shutdown_complete = True
        self._closing = True
        self._size_recalc_timer.stop()
        self._flush_pending_folder_icon_size_changes()
        self._size_service.shutdown()
        ffmpeg_task = getattr(self, "_ffmpeg_download_task", None)
        if ffmpeg_task is not None:
            ffmpeg_task.cancel()
        if self._owns_shared_services:
            self._folder_count_service.shutdown()
            self._appimage_icon_service.shutdown()
        self.desktop_process_manager.shutdown()
        self._shutdown_broken_entries_scan_worker()
        self.persist_toolbox_state()
        self._save_settings()
        if self._state_repository is not None:
            try:
                self._state_repository.state_changed.disconnect(
                    self._on_shared_toolbox_state_changed
                )
            except (RuntimeError, TypeError):
                pass
        if self._settings_controller is not None:
            try:
                self._settings_controller.settings_changed.disconnect(
                    self._on_shared_settings_changed
                )
            except (RuntimeError, TypeError):
                pass
        try:
            self._folder_browse_appearance_store.icon_size_changed.disconnect(
                self._on_folder_browse_appearance_changed
            )
        except (RuntimeError, TypeError):
            pass

    def _setup_ui(self) -> None:
        central_widget, self.widgets = UIBuilder.create_main_layout()
        self.setCentralWidget(central_widget)
        self.tab_widget = self.widgets[constants.WIDGET_TABS]
        self.settings_tab = self.widgets[constants.WIDGET_SETTINGS_TAB]
        self.help_tab = self.widgets[constants.WIDGET_HELP_TAB]
        self._new_toolbox_tab_action_page = QtWidgets.QWidget(self.tab_widget)
        self._new_toolbox_tab_action_page.setObjectName(
            "new_toolbox_tab_action_page"
        )
        self._new_toolbox_tab_button: QtWidgets.QToolButton | None = None
        
        self.tab_size_label = QtWidgets.QLabel("")
        self.status.addPermanentWidget(self.tab_size_label)

        self.tab_widget.setMovable(False)
        self.tab_widget.currentChanged.connect(self._on_current_tab_changed)
        self._new_toolbox_tab_shortcut = QtGui.QShortcut(
            QtGui.QKeySequence("Ctrl+T"),
            self,
        )
        self._new_toolbox_tab_shortcut.setContext(
            QtCore.Qt.ShortcutContext.ApplicationShortcut
        )
        self._new_toolbox_tab_shortcut.activated.connect(
            self._create_new_toolbox_tab
        )
        self._new_window_shortcut = QtGui.QShortcut(
            QtGui.QKeySequence("Ctrl+N"),
            self,
        )
        self._new_window_shortcut.setContext(
            QtCore.Qt.ShortcutContext.ApplicationShortcut
        )
        self._new_window_shortcut.activated.connect(self.new_window_requested)

        tab_bar = self.tab_widget.tabBar()
        tab_bar.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        tab_bar.customContextMenuRequested.connect(self._show_tab_context_menu)

        if not self._managed:
            self._setup_system_tray()
        self._connect_settings_widgets()

    def _setup_system_tray(self) -> None:
        if not QtWidgets.QSystemTrayIcon.isSystemTrayAvailable():
            return

        self.tray_icon = QtWidgets.QSystemTrayIcon(self)

        tray_icon_path = None
        # Try to find one_tray.png next to the main icon
        app_icon_candidate = getattr(sys, "_MEIPASS", None)
        if app_icon_candidate:
            packaged = Path(app_icon_candidate) / "app" / "assets" / "one_tray.png"
            if packaged.is_file():
                tray_icon_path = packaged
        if not tray_icon_path:
            candidate = Path(__file__).resolve().parent / "assets" / "one_tray.png"
            if candidate.is_file():
                tray_icon_path = candidate

        if tray_icon_path:
            self.tray_icon.setIcon(self._tray_sized_icon(QtGui.QIcon(str(tray_icon_path))))
        else:
            app_icon = QtWidgets.QApplication.instance().windowIcon()
            if not app_icon.isNull():
                self.tray_icon.setIcon(self._tray_sized_icon(app_icon))
            else:
                icon = QtGui.QIcon.fromTheme("applications-system", self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DesktopIcon))
                self.tray_icon.setIcon(self._tray_sized_icon(icon))

        tray_menu = QtWidgets.QMenu(self)

        show_action = tray_menu.addAction("Toolbox anzeigen")
        show_action.triggered.connect(self._show_from_tray)

        tray_menu.addSeparator()

        quit_action = tray_menu.addAction("Beenden")
        quit_action.triggered.connect(self._quit_from_tray)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.hide()

    @staticmethod
    def _tray_sized_icon(icon: QtGui.QIcon) -> QtGui.QIcon:
        pixmap = icon.pixmap(64, 64)
        return QtGui.QIcon(pixmap) if not pixmap.isNull() else icon

    def _sync_tray_state(self) -> None:
        if self._managed:
            manager = getattr(self, "_window_manager", None)
            if manager is not None:
                manager.sync_tray_from_window(self)
            return
        app = QtWidgets.QApplication.instance()
        tray_available = bool(
            self.tray_icon is not None
            and QtWidgets.QSystemTrayIcon.isSystemTrayAvailable()
        )
        if self.tray_icon is not None:
            self.tray_icon.setVisible(self._show_tray_icon and tray_available)
        if app is not None:
            minimize_enabled = bool(
                self._show_tray_icon and self._minimize_to_tray and tray_available
            )
            app.setQuitOnLastWindowClosed(not minimize_enabled)

    def _update_tray_settings_controls_enabled(self) -> None:
        show_checkbox = self.widgets.get(constants.WIDGET_SHOW_TRAY_ICON_CHECKBOX)
        minimize_checkbox = self.widgets.get(
            constants.WIDGET_MINIMIZE_TO_TRAY_CHECKBOX
        )
        if show_checkbox is None or minimize_checkbox is None:
            return
        show_enabled = bool(show_checkbox.isChecked())
        if not show_enabled and minimize_checkbox.isChecked():
            minimize_checkbox.blockSignals(True)
            minimize_checkbox.setChecked(False)
            minimize_checkbox.blockSignals(False)
        minimize_checkbox.setEnabled(show_enabled)

    def _on_show_tray_icon_changed(self, _checked: bool) -> None:
        self._update_tray_settings_controls_enabled()
        self._on_system_settings_changed()

    def _show_from_tray(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _quit_from_tray(self) -> None:
        self._force_quit = True
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.quit()

    def _on_tray_activated(self, reason: QtWidgets.QSystemTrayIcon.ActivationReason) -> None:
        if reason == QtWidgets.QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self._show_from_tray()

    def _connect_settings_widgets(self) -> None:
        for widget_name in (
            constants.WIDGET_ICON_SIZE_SLIDER,
            constants.WIDGET_TILE_FONT_SIZE_SLIDER,
            constants.WIDGET_TILE_FRAME_THICKNESS_SLIDER,
            constants.WIDGET_GRID_SPACING_X_SLIDER,
            constants.WIDGET_GRID_SPACING_Y_SLIDER,
            constants.WIDGET_SECTION_FONT_SIZE_SLIDER,
            constants.WIDGET_SECTION_LINE_THICKNESS_SLIDER,
        ):
            slider = self.widgets[widget_name]
            slider.valueChanged.connect(self._on_layout_settings_changed)

        tile_font_auto = self.widgets[constants.WIDGET_TILE_FONT_AUTO_CHECKBOX]
        tile_font_auto.toggled.connect(self._on_tile_font_auto_changed)

        frame_checkbox = self.widgets[constants.WIDGET_TILE_FRAME_ENABLED_CHECKBOX]
        frame_checkbox.toggled.connect(self._on_layout_settings_changed)
        image_preview_checkbox = self.widgets[constants.WIDGET_IMAGE_FILE_PREVIEW_CHECKBOX]
        image_preview_checkbox.toggled.connect(self._on_layout_settings_changed)
        image_preview_mode_combobox = self.widgets[constants.WIDGET_IMAGE_FILE_PREVIEW_MODE_COMBOBOX]
        image_preview_mode_combobox.currentIndexChanged.connect(self._on_layout_settings_changed)
        
        preview_overlay_checkbox = self.widgets.get(constants.WIDGET_PREVIEW_OVERLAY_CHECKBOX)
        if preview_overlay_checkbox:
            preview_overlay_checkbox.toggled.connect(self._on_layout_settings_changed)
        video_preview_checkbox = self.widgets[constants.WIDGET_VIDEO_FILE_PREVIEW_CHECKBOX]
        video_preview_checkbox.toggled.connect(self._on_layout_settings_changed)
        hover_preview_checkbox = self.widgets[constants.WIDGET_HOVER_PREVIEW_CHECKBOX]
        hover_preview_checkbox.toggled.connect(self._on_layout_settings_changed)
        show_tooltips_checkbox = self.widgets[constants.WIDGET_SHOW_TOOLTIPS_CHECKBOX]
        show_tooltips_checkbox.toggled.connect(self._on_layout_settings_changed)
        ffmpeg_manual_path_input = self.widgets[constants.WIDGET_FFMPEG_MANUAL_PATH_INPUT]
        ffmpeg_manual_path_input.editingFinished.connect(self._on_ffmpeg_manual_path_changed)
        ffmpeg_manual_path_button = self.widgets[constants.WIDGET_FFMPEG_MANUAL_PATH_BUTTON]
        ffmpeg_manual_path_button.clicked.connect(self._choose_ffmpeg_manual_path)
        ffmpeg_rescan_button = self.widgets[constants.WIDGET_FFMPEG_RESCAN_BUTTON]
        ffmpeg_rescan_button.clicked.connect(self._rescan_ffmpeg_status)
        ffmpeg_download_button = self.widgets["ffmpeg_download_button"]
        ffmpeg_download_button.clicked.connect(self._download_internal_ffmpeg)

        auto_compact_left_checkbox = self.widgets[constants.WIDGET_AUTO_COMPACT_LEFT_CHECKBOX]
        auto_compact_left_checkbox.toggled.connect(self._on_layout_settings_changed)

        tab_manager_list = self.widgets[constants.WIDGET_TAB_MANAGER_LIST]
        tab_manager_list.itemChanged.connect(self._on_tab_manager_item_changed)
        tab_manager_list.currentRowChanged.connect(self._update_tab_manager_buttons_enabled)

        move_up_button = self.widgets[constants.BUTTON_TAB_MOVE_UP]
        move_up_button.clicked.connect(lambda: self._move_selected_tab_in_manager(-1))

        move_down_button = self.widgets[constants.BUTTON_TAB_MOVE_DOWN]
        move_down_button.clicked.connect(lambda: self._move_selected_tab_in_manager(1))

        tile_frame_color_input = self.widgets[constants.WIDGET_TILE_FRAME_COLOR_INPUT]
        tile_frame_color_input.editingFinished.connect(self._on_tile_frame_color_changed)

        tile_frame_color_button = self.widgets[constants.WIDGET_TILE_FRAME_COLOR_BUTTON]
        tile_frame_color_button.clicked.connect(self._choose_tile_frame_color)

        tile_highlight_color_input = self.widgets[constants.WIDGET_TILE_HIGHLIGHT_COLOR_INPUT]
        tile_highlight_color_input.editingFinished.connect(self._on_tile_highlight_color_changed)

        tile_highlight_color_button = self.widgets[constants.WIDGET_TILE_HIGHLIGHT_COLOR_BUTTON]
        tile_highlight_color_button.clicked.connect(self._choose_tile_highlight_color)

        icon_preview_bg_input = self.widgets[constants.WIDGET_ICON_PREVIEW_BACKGROUND_COLOR_INPUT]
        icon_preview_bg_input.editingFinished.connect(self._on_icon_preview_background_color_changed)

        icon_preview_bg_button = self.widgets[constants.WIDGET_ICON_PREVIEW_BACKGROUND_COLOR_BUTTON]
        icon_preview_bg_button.clicked.connect(self._choose_icon_preview_background_color)

        tool_launch_mode_combobox = self.widgets[constants.WIDGET_TOOL_LAUNCH_MODE_COMBOBOX]
        tool_launch_mode_combobox.currentIndexChanged.connect(self._on_tool_launch_mode_changed)

        for widget_name in (
            constants.WIDGET_SECTION_GAP_ABOVE_SPINBOX,
            constants.WIDGET_SECTION_GAP_BELOW_SPINBOX,
        ):
            gap_spinbox = self.widgets.get(widget_name)
            if gap_spinbox is not None:
                gap_spinbox.valueChanged.connect(self._on_layout_settings_changed)

        color_input = self.widgets[constants.WIDGET_SECTION_LINE_COLOR_INPUT]
        color_input.editingFinished.connect(self._on_section_line_color_changed)

        color_button = self.widgets[constants.WIDGET_SECTION_LINE_COLOR_BUTTON]
        color_button.clicked.connect(self._choose_section_line_color)

        section_color_list = self.widgets[constants.WIDGET_SECTION_COLOR_LIST]
        section_color_list.currentRowChanged.connect(self._on_section_color_selection_changed)

        selected_line_input = self.widgets[constants.WIDGET_SECTION_SELECTED_LINE_COLOR_INPUT]
        selected_line_input.editingFinished.connect(self._on_selected_section_line_color_changed)
        selected_line_button = self.widgets[constants.WIDGET_SECTION_SELECTED_LINE_COLOR_BUTTON]
        selected_line_button.clicked.connect(self._choose_selected_section_line_color)
        selected_line_apply = self.widgets[constants.BUTTON_SECTION_APPLY_SELECTED_LINE_COLOR]
        selected_line_apply.clicked.connect(self._apply_selected_section_line_color)

        selected_title_input = self.widgets[constants.WIDGET_SECTION_SELECTED_TITLE_COLOR_INPUT]
        selected_title_input.editingFinished.connect(self._on_selected_section_title_color_changed)
        selected_title_button = self.widgets[constants.WIDGET_SECTION_SELECTED_TITLE_COLOR_BUTTON]
        selected_title_button.clicked.connect(self._choose_selected_section_title_color)
        selected_title_apply = self.widgets[constants.BUTTON_SECTION_APPLY_SELECTED_TITLE_COLOR]
        selected_title_apply.clicked.connect(self._apply_selected_section_title_color)

        all_line_input = self.widgets[constants.WIDGET_SECTION_ALL_LINE_COLOR_INPUT]
        all_line_input.editingFinished.connect(self._on_all_section_line_color_changed)
        all_line_button = self.widgets[constants.WIDGET_SECTION_ALL_LINE_COLOR_BUTTON]
        all_line_button.clicked.connect(self._choose_all_section_line_color)
        all_line_apply = self.widgets[constants.BUTTON_SECTION_APPLY_ALL_LINE_COLOR]
        all_line_apply.clicked.connect(self._apply_all_section_line_color)

        all_title_input = self.widgets[constants.WIDGET_SECTION_ALL_TITLE_COLOR_INPUT]
        all_title_input.editingFinished.connect(self._on_all_section_title_color_changed)
        all_title_button = self.widgets[constants.WIDGET_SECTION_ALL_TITLE_COLOR_BUTTON]
        all_title_button.clicked.connect(self._choose_all_section_title_color)
        all_title_apply = self.widgets[constants.BUTTON_SECTION_APPLY_ALL_TITLE_COLOR]
        all_title_apply.clicked.connect(self._apply_all_section_title_color)

        for button_name in (
            constants.BUTTON_SECTION_QUICK_ALL_LINE_DEFAULT,
            constants.BUTTON_SECTION_QUICK_ALL_LINE_GRAY,
            constants.BUTTON_SECTION_QUICK_ALL_LINE_BLUE,
            constants.BUTTON_SECTION_QUICK_ALL_LINE_GREEN,
            constants.BUTTON_SECTION_QUICK_ALL_LINE_RED,
        ):
            quick_button = self.widgets[button_name]
            quick_button.clicked.connect(lambda _=False, name=button_name: self._apply_quick_all_section_line_color(name))

        for button_name in (
            constants.BUTTON_SECTION_QUICK_ALL_TITLE_DEFAULT,
            constants.BUTTON_SECTION_QUICK_ALL_TITLE_WHITE,
            constants.BUTTON_SECTION_QUICK_ALL_TITLE_AMBER,
            constants.BUTTON_SECTION_QUICK_ALL_TITLE_CYAN,
            constants.BUTTON_SECTION_QUICK_ALL_TITLE_RED,
        ):
            quick_button = self.widgets[button_name]
            quick_button.clicked.connect(
                lambda _=False, name=button_name: self._apply_quick_all_section_title_color(name)
            )

        export_button = self.widgets[constants.WIDGET_EXPORT_PROFILE_BUTTON]
        export_button.clicked.connect(self._export_profile_json)

        import_button = self.widgets[constants.WIDGET_IMPORT_PROFILE_BUTTON]
        import_button.clicked.connect(self._import_profile_json)

        check_broken_entries_button = self.widgets[constants.BUTTON_CHECK_BROKEN_ENTRIES]
        check_broken_entries_button.clicked.connect(self._run_broken_entries_check)

        apply_settings_button = self.widgets[constants.BUTTON_APPLY_SETTINGS]
        apply_settings_button.clicked.connect(self._apply_pending_settings)

        # System behavior checkboxes — must mark dirty so Apply is enabled
        show_tray_icon_cb = self.widgets.get(constants.WIDGET_SHOW_TRAY_ICON_CHECKBOX)
        if show_tray_icon_cb is not None:
            show_tray_icon_cb.toggled.connect(self._on_show_tray_icon_changed)

        minimize_tray_cb = self.widgets.get(constants.WIDGET_MINIMIZE_TO_TRAY_CHECKBOX)
        if minimize_tray_cb is not None:
            minimize_tray_cb.toggled.connect(self._on_system_settings_changed)

        second_launch_combo = self.widgets.get(
            constants.WIDGET_SECOND_LAUNCH_ACTION_COMBOBOX
        )
        if second_launch_combo is not None:
            second_launch_combo.currentIndexChanged.connect(
                self._on_system_settings_changed
            )

        folder_click_cb = self.widgets.get(constants.WIDGET_FOLDER_SINGLE_CLICK_CHECKBOX)
        if folder_click_cb is not None:
            folder_click_cb.toggled.connect(self._on_system_settings_changed)

        folder_file_count_cb = self.widgets.get(constants.WIDGET_FOLDER_SHOW_FILE_COUNT_CHECKBOX)
        if folder_file_count_cb is not None:
            folder_file_count_cb.toggled.connect(self._on_layout_settings_changed)

        file_assoc_system_cb = self.widgets.get(constants.WIDGET_FILE_ASSOC_USE_SYSTEM_CHECKBOX)
        if file_assoc_system_cb is not None:
            file_assoc_system_cb.toggled.connect(self._on_system_settings_changed)
        for widget_name in (
            constants.WIDGET_FILE_ASSOC_AUDIO_INPUT,
            constants.WIDGET_FILE_ASSOC_VIDEO_INPUT,
            constants.WIDGET_FILE_ASSOC_IMAGE_INPUT,
            constants.WIDGET_FILE_ASSOC_PDF_INPUT,
            constants.WIDGET_FILE_ASSOC_DOCUMENT_INPUT,
        ):
            association_input = self.widgets.get(widget_name)
            if association_input is not None:
                association_input.textChanged.connect(self._on_system_settings_changed)


    def eventFilter(self, watched: QtCore.QObject, event: QtCore.QEvent) -> bool:
        ctx = self._drop_widget_map.get(watched)
        if ctx is not None:
            if event.type() == QtCore.QEvent.Type.DragEnter:
                drag_event = event  # type: ignore[assignment]
                if self._mime_contains_supported_paths(drag_event.mimeData()):
                    drag_event.acceptProposedAction()
                    return True
                return False
            if event.type() == QtCore.QEvent.Type.Drop:
                drop_event = event  # type: ignore[assignment]
                file_paths = self._extract_supported_paths(drop_event.mimeData())
                if file_paths:
                    self.add_tool_paths(ctx, file_paths)
                    drop_event.acceptProposedAction()
                return True
        return super().eventFilter(watched, event)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.matches(QtGui.QKeySequence.StandardKey.Undo):
            self._undo_last_toolbox_change()
            event.accept()
            return
        if event.matches(QtGui.QKeySequence.StandardKey.Redo):
            self._redo_last_toolbox_change()
            event.accept()
            return
        if event.key() in (QtCore.Qt.Key.Key_Delete, QtCore.Qt.Key.Key_Backspace):
            ctx = self.current_toolbox_context()
            if ctx is not None and ctx.selected_ids:
                self.remove_selected(ctx)
                event.accept()
                return
        super().keyPressEvent(event)

    def _on_current_tab_changed(self, index: int) -> None:
        previous_widget = None
        if 0 <= self._last_tab_index < self.tab_widget.count():
            previous_widget = self.tab_widget.widget(self._last_tab_index)
        current_widget = self.tab_widget.widget(index)
        target_ctx = self._toolbox_context_for_index(index)
        should_auto_apply = (
            not self._auto_applying_settings_on_tab_change
            and previous_widget is self.settings_tab
            and target_ctx is not None
            and current_widget is not self.settings_tab
            and bool(getattr(self, "_settings_dirty", False))
        )
        if should_auto_apply:
            self._auto_applying_settings_on_tab_change = True
            try:
                self._apply_pending_settings()
            finally:
                self._auto_applying_settings_on_tab_change = False
            index = self.tab_widget.currentIndex()

        ctx: Optional[ToolboxTabContext] = self._toolbox_context_for_index(index)

        if hasattr(self, "_update_corner_button_active_state"):
            self._update_corner_button_active_state(current_widget)

        if ctx is not None:
            self._update_managed_window_title()
            self._update_details(ctx)
            self._update_action_buttons(ctx)
            self._update_window_minimum_width(ctx)
            self._recalculate_active_tab_size(ctx)
        elif self.tab_widget.widget(index) is self.settings_tab:
            self.tab_size_label.setText("")
            self._refresh_section_color_manager()
            self._update_ffmpeg_status_preview()
        else:
            self.tab_size_label.setText("")
            
        self._last_tab_index = index

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        if self._managed:
            manager = getattr(self, "_window_manager", None)
            if manager is not None and manager.handle_close_event(self, event):
                return
            self._begin_shutdown()
            self.window_closing.emit(self.window_id)
            super().closeEvent(event)
            return
        tray_enabled = bool(
            not self._force_quit
            and self._show_tray_icon
            and self._minimize_to_tray
            and self.tray_icon is not None
            and QtWidgets.QSystemTrayIcon.isSystemTrayAvailable()
        )
        if tray_enabled:
            event.ignore()
            self.persist_toolbox_state()
            self._save_settings()
            self.hide()
            self.tray_icon.showMessage(
                "Toolbox läuft im Hintergrund",
                "Die Toolbox wurde in den Tray minimiert.",
                QtWidgets.QSystemTrayIcon.MessageIcon.Information,
                2000,
            )
            return
        self._begin_shutdown()
        super().closeEvent(event)
