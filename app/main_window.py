#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Main window orchestration for the toolbox launcher."""

from __future__ import annotations

import weakref
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from app import constants
from app.domain.tab_context import ToolboxTabContext
from app.features.entries.controller import MainWindowEntriesMixin
from app.features.settings.controller import MainWindowSettingsMixin
from app.features.tabs.controller import MainWindowTabsMixin
from app.services.system_utils import get_config_directory
from app.ui.layouts import UIBuilder


class MainWindow(
    MainWindowEntriesMixin,
    MainWindowSettingsMixin,
    MainWindowTabsMixin,
    QtWidgets.QMainWindow,
):
    """Main application window for the EXE/shortcut toolbox."""

    def __init__(self, app_name: str, config_dir: Path | None = None):
        super().__init__()
        self.app_name = app_name or constants.DEFAULT_APP_NAME
        self.setWindowTitle(self.app_name)

        self.config_dir = (
            config_dir if config_dir is not None else get_config_directory(self.app_name)
        )
        self.icon_provider = QtWidgets.QFileIconProvider()
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
        self._undo_stack: list[list[dict[str, object]]] = []
        self._redo_stack: list[list[dict[str, object]]] = []
        self._undo_last_state: list[dict[str, object]] | None = None
        self._undo_suspended = False
        self._undo_max_steps = 50
        self._initialize_applied_settings_defaults()

        self.status = self.statusBar()
        self.status.showMessage("Ready")

        self._setup_ui()
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self._persist_on_quit)
        self._load_toolbox_state()
        self._load_settings()
        self.refresh_all_canvases()
        self._initialize_undo_history()
        self._settings_ready = True

    def _persist_on_quit(self) -> None:
        self._shutdown_broken_entries_scan_worker()
        self.persist_toolbox_state()
        self._save_settings()

    def _setup_ui(self) -> None:
        central_widget, self.widgets = UIBuilder.create_main_layout()
        self.setCentralWidget(central_widget)
        self.tab_widget = self.widgets[constants.WIDGET_TABS]
        self.settings_tab = self.widgets[constants.WIDGET_SETTINGS_TAB]
        self.help_tab = self.widgets[constants.WIDGET_HELP_TAB]

        self.tab_widget.setMovable(False)
        self.tab_widget.currentChanged.connect(self._on_current_tab_changed)

        tab_bar = self.tab_widget.tabBar()
        tab_bar.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        tab_bar.customContextMenuRequested.connect(self._show_tab_context_menu)

        self._connect_settings_widgets()

    def _connect_settings_widgets(self) -> None:
        for widget_name in (
            constants.WIDGET_ICON_SIZE_SLIDER,
            constants.WIDGET_TILE_FRAME_THICKNESS_SLIDER,
            constants.WIDGET_GRID_SPACING_X_SLIDER,
            constants.WIDGET_GRID_SPACING_Y_SLIDER,
            constants.WIDGET_SECTION_FONT_SIZE_SLIDER,
            constants.WIDGET_SECTION_LINE_THICKNESS_SLIDER,
        ):
            slider = self.widgets[widget_name]
            slider.valueChanged.connect(self._on_layout_settings_changed)

        frame_checkbox = self.widgets[constants.WIDGET_TILE_FRAME_ENABLED_CHECKBOX]
        frame_checkbox.toggled.connect(self._on_layout_settings_changed)

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
        ctx: Optional[ToolboxTabContext] = self._toolbox_context_for_index(index)
        if ctx is not None:
            self._update_details(ctx)
            self._update_action_buttons(ctx)
            self._update_window_minimum_width(ctx)
        elif self.tab_widget.widget(index) is self.settings_tab:
            self._refresh_section_color_manager()
        self._save_settings()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self._shutdown_broken_entries_scan_worker()
        self.persist_toolbox_state()
        self._save_settings()
        super().closeEvent(event)
