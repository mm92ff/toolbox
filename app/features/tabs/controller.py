#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tab lifecycle behavior split out from MainWindow."""

from __future__ import annotations

import copy
from typing import Optional

from PySide6 import QtCore, QtGui, QtWidgets

from app import constants
from app.domain.models import ToolboxEntry, ToolboxTabData
from app.domain.tab_context import ToolboxTabContext
from app.features.tabs.tab_manager import MainWindowTabManagerMixin
from app.services.storage import load_toolbox_tabs, save_toolbox_tabs
from app.state.toolbox_repository import StaleToolboxStateError
from app.ui.layouts import UIBuilder


class MainWindowTabsMixin(MainWindowTabManagerMixin):
    @staticmethod
    def _normalize_tab_background_color(value: str) -> str:
        color = QtGui.QColor((value or "").strip())
        if not color.isValid():
            return ""
        return color.name()

    def _apply_tab_background_color(self, ctx: ToolboxTabContext) -> None:
        normalized = self._normalize_tab_background_color(ctx.background_color)
        ctx.background_color = normalized
        ctx.canvas.set_background_color(normalized)

    def _collect_toolbox_state_dicts(self) -> list[dict[str, object]]:
        return [tab.to_dict() for tab in self._collect_toolbox_state()]

    @staticmethod
    def _toolbox_state_from_dicts(state: list[dict[str, object]]) -> list[ToolboxTabData]:
        tabs: list[ToolboxTabData] = []
        for raw_tab in state:
            if not isinstance(raw_tab, dict):
                continue
            tabs.append(ToolboxTabData.from_dict(raw_tab))
        return tabs

    @staticmethod
    def _normalize_primary_tabs(tabs: list[ToolboxTabData]) -> None:
        if not tabs:
            return
        primary_indices = [index for index, tab in enumerate(tabs) if tab.is_primary]
        if not primary_indices:
            tabs[0].is_primary = True
            return
        first_primary = primary_indices[0]
        for index, tab in enumerate(tabs):
            tab.is_primary = index == first_primary

    def _initialize_undo_history(self) -> None:
        if getattr(self, "_state_repository", None) is not None:
            self._undo_stack.clear()
            self._redo_stack.clear()
            self._undo_last_state = copy.deepcopy(self._collect_toolbox_state_dicts())
            return
        self._undo_stack.clear()
        self._redo_stack.clear()
        self._undo_last_state = copy.deepcopy(self._collect_toolbox_state_dicts())

    def _record_undo_snapshot_before_persist(self, current_state: list[dict[str, object]]) -> None:
        if self._undo_suspended:
            return
        if self._undo_last_state is None:
            self._undo_last_state = copy.deepcopy(current_state)
            return
        if current_state == self._undo_last_state:
            return
        self._undo_stack.append(copy.deepcopy(self._undo_last_state))
        if len(self._undo_stack) > self._undo_max_steps:
            self._undo_stack = self._undo_stack[-self._undo_max_steps :]
        self._redo_stack.clear()

    def _apply_toolbox_state_dicts(self, state: list[dict[str, object]]) -> None:
        tabs = self._toolbox_state_from_dicts(state)
        if not tabs:
            tabs = [
                ToolboxTabData(
                    title=constants.DEFAULT_TOOLBOX_TAB_TITLE,
                    entries=[],
                    is_primary=True,
                )
            ]
        self._normalize_primary_tabs(tabs)

        current_widget = self.tab_widget.currentWidget()
        preferred_ctx = self.current_toolbox_context()
        preferred_tab_id = preferred_ctx.tab_id if preferred_ctx is not None else None
        preferred_index = (
            self.toolbox_tabs.index(preferred_ctx) if preferred_ctx is not None else 0
        )
        existing_by_id = {ctx.tab_id: ctx for ctx in self.toolbox_tabs}
        reconciled_contexts: list[ToolboxTabContext] = []
        for tab_data in tabs:
            restored = existing_by_id.pop(tab_data.tab_id, None)
            if restored is None:
                restored = self._create_toolbox_tab(
                    tab_data.title,
                    tab_data.entries,
                    tab_data.tab_id,
                    tab_data.is_primary,
                    tab_data.background_color,
                    rebuild_tabs=False,
                )
            else:
                restored.title = tab_data.title
                restored.is_primary = tab_data.is_primary
                restored.background_color = self._normalize_tab_background_color(
                    tab_data.background_color
                )
                restored.entries = self._reconcile_entry_models(
                    restored.entries, tab_data.entries
                )
                available_ids = {entry.entry_id for entry in restored.entries}
                restored.selected_ids.intersection_update(available_ids)
                self._apply_tab_background_color(restored)
            reconciled_contexts.append(restored)

        for removed in existing_by_id.values():
            if self._folder_icon_size_change_pending(removed):
                self._commit_folder_icon_size_change(removed)
            for widget in (
                removed.drop_zone,
                removed.canvas.viewport(),
                removed.canvas.surface,
            ):
                self._drop_widget_map.pop(widget, None)
                widget.removeEventFilter(self)
            removed.page.deleteLater()
        self.toolbox_tabs = reconciled_contexts

        preferred_widget = self.settings_tab
        if current_widget is self.help_tab:
            preferred_widget = self.help_tab
        elif current_widget is self.settings_tab:
            preferred_widget = self.settings_tab
        elif preferred_tab_id is not None:
            restored_ctx = next(
                (ctx for ctx in self.toolbox_tabs if ctx.tab_id == preferred_tab_id),
                None,
            )
            if restored_ctx is not None:
                preferred_widget = restored_ctx.page
            elif self.toolbox_tabs:
                fallback_index = min(preferred_index, len(self.toolbox_tabs) - 1)
                preferred_widget = self.toolbox_tabs[fallback_index].page
        selected_key = self._selected_tab_manager_key()
        self._reinsert_fixed_tabs(preferred_widget=preferred_widget)
        self._refresh_tab_manager_ui(preferred_key=selected_key)
        self.refresh_all_canvases()
        for ctx in self.toolbox_tabs:
            if ctx.browse_stack:
                from app.features.entries.folder_browse import _refresh_browse_view

                if not _refresh_browse_view(self, ctx):
                    ctx.browse_stack.clear()
        if hasattr(self, "_update_managed_window_title"):
            self._update_managed_window_title()

    @staticmethod
    def _reconcile_entry_models(
        current: list[ToolboxEntry], incoming: list[ToolboxEntry]
    ) -> list[ToolboxEntry]:
        """Keep existing entry identities while applying canonical model fields."""

        existing = {entry.entry_id: entry for entry in current}
        reconciled: list[ToolboxEntry] = []
        field_names = (
            "title",
            "kind",
            "path",
            "x",
            "y",
            "always_run_as_admin",
            "launch_arguments",
            "launch_working_directory",
            "launch_wait",
            "launch_window_style",
            "section_line_color",
            "section_title_color",
            "custom_title",
            "custom_icon_path",
        )
        for source in incoming:
            target = existing.get(source.entry_id)
            if target is None:
                target = ToolboxEntry.from_dict(source.to_dict())
            else:
                for field_name in field_names:
                    setattr(target, field_name, getattr(source, field_name))
            reconciled.append(target)
        return reconciled

    def _undo_last_toolbox_change(self) -> None:
        repository = getattr(self, "_state_repository", None)
        if repository is not None:
            if repository.undo(getattr(self, "window_id", "")):
                self.status.showMessage("Undid last toolbox change.", 2500)
            else:
                self.status.showMessage("Nothing to undo.", 2500)
            return
        if not self._undo_stack:
            self.status.showMessage("Nothing to undo.", 2500)
            return

        current_state = copy.deepcopy(self._collect_toolbox_state_dicts())
        previous_state = self._undo_stack.pop()
        if current_state != previous_state:
            self._redo_stack.append(current_state)
            if len(self._redo_stack) > self._undo_max_steps:
                self._redo_stack = self._redo_stack[-self._undo_max_steps :]
        self._undo_suspended = True
        try:
            self._apply_toolbox_state_dicts(previous_state)
            tabs = self._toolbox_state_from_dicts(previous_state)
            self._normalize_primary_tabs(tabs)
            save_toolbox_tabs(self.config_dir, tabs)
            self._undo_last_state = copy.deepcopy(previous_state)
        finally:
            self._undo_suspended = False
        self.status.showMessage("Undid last toolbox change.", 2500)

    def _redo_last_toolbox_change(self) -> None:
        repository = getattr(self, "_state_repository", None)
        if repository is not None:
            if repository.redo(getattr(self, "window_id", "")):
                self.status.showMessage("Redid last toolbox change.", 2500)
            else:
                self.status.showMessage("Nothing to redo.", 2500)
            return
        if not self._redo_stack:
            self.status.showMessage("Nothing to redo.", 2500)
            return

        current_state = copy.deepcopy(self._collect_toolbox_state_dicts())
        next_state = self._redo_stack.pop()
        if current_state != next_state:
            self._undo_stack.append(current_state)
            if len(self._undo_stack) > self._undo_max_steps:
                self._undo_stack = self._undo_stack[-self._undo_max_steps :]
        self._undo_suspended = True
        try:
            self._apply_toolbox_state_dicts(next_state)
            tabs = self._toolbox_state_from_dicts(next_state)
            self._normalize_primary_tabs(tabs)
            save_toolbox_tabs(self.config_dir, tabs)
            self._undo_last_state = copy.deepcopy(next_state)
        finally:
            self._undo_suspended = False
        self.status.showMessage("Redid last toolbox change.", 2500)

    def _clear_toolbox_tabs(self) -> None:
        for ctx in list(self.toolbox_tabs):
            if self._folder_icon_size_change_pending(ctx):
                self._commit_folder_icon_size_change(ctx)
            for widget in (ctx.drop_zone, ctx.canvas.viewport(), ctx.canvas.surface):
                self._drop_widget_map.pop(widget, None)
                widget.removeEventFilter(self)
            tab_index = self.tab_widget.indexOf(ctx.page)
            if tab_index >= 0:
                self.tab_widget.removeTab(tab_index)
            ctx.page.deleteLater()
        self.toolbox_tabs.clear()
        self._reinsert_fixed_tabs()
        self._refresh_tab_manager_ui()

    def _create_toolbox_tab(
        self,
        title: str,
        entries: Optional[list[ToolboxEntry]] = None,
        tab_id: Optional[str] = None,
        is_primary: bool = False,
        background_color: str = "",
        insert_position: Optional[int] = None,
        switch_to: bool = False,
        rebuild_tabs: bool = True,
    ) -> ToolboxTabContext:
        page, widgets = UIBuilder.create_toolbox_tab()
        ctx = ToolboxTabContext(
            page=page,
            splitter=widgets[constants.WIDGET_TOOLBOX_SPLITTER],  # type: ignore[arg-type]
            drop_zone=widgets[constants.WIDGET_DROP_ZONE],
            search_input=widgets[constants.WIDGET_SEARCH_INPUT],  # type: ignore[arg-type]
            canvas=widgets[constants.WIDGET_TOOL_CANVAS],  # type: ignore[arg-type]
            details_label=widgets[constants.WIDGET_TOOL_DETAILS],  # type: ignore[arg-type]
            add_tool_button=widgets[constants.BUTTON_ADD_TOOL],  # type: ignore[arg-type]
            add_section_button=widgets[constants.BUTTON_ADD_SECTION],  # type: ignore[arg-type]
            launch_button=widgets[constants.BUTTON_LAUNCH_TOOL],  # type: ignore[arg-type]
            remove_button=widgets[constants.BUTTON_REMOVE_TOOL],  # type: ignore[arg-type]
            open_config_button=widgets[constants.BUTTON_OPEN_CONFIG],  # type: ignore[arg-type]
            entries=list(entries or []),
            title=title or constants.DEFAULT_TOOLBOX_TAB_TITLE,
            tab_id=tab_id
            or QtCore.QUuid.createUuid().toString(QtCore.QUuid.StringFormat.WithoutBraces),
            is_primary=is_primary,
            background_color=self._normalize_tab_background_color(background_color),
            selected_ids=set(),
        )
        ctx.canvas.surface.set_folder_count_service(self._folder_count_service)
        ctx.canvas.surface.set_appimage_icon_service(self._appimage_icon_service)
        ctx.canvas.set_thumbnail_cache_dir(self.config_dir / "thumbnail_cache")

        ctx.add_tool_button.clicked.connect(lambda _=False, c=ctx: self.add_tools_from_dialog(c))
        ctx.add_section_button.clicked.connect(lambda _=False, c=ctx: self.add_section(c))
        ctx.launch_button.clicked.connect(lambda _=False, c=ctx: self.launch_selected(c))
        ctx.remove_button.clicked.connect(lambda _=False, c=ctx: self.remove_selected(c))
        ctx.open_config_button.clicked.connect(self._open_config_directory)

        # Wire breadcrumb back button
        breadcrumb_bar = widgets.get(constants.WIDGET_BROWSE_BREADCRUMB_BAR)
        ctx.breadcrumb_bar = breadcrumb_bar
        ctx.browse_path_label = widgets.get(constants.WIDGET_BROWSE_PATH_LABEL)  # type: ignore[assignment]
        ctx.browse_icon_size_slider = widgets.get(  # type: ignore[assignment]
            constants.WIDGET_BROWSE_ICON_SIZE_SLIDER
        )
        ctx.browse_icon_size_value_label = widgets.get(  # type: ignore[assignment]
            constants.WIDGET_BROWSE_ICON_SIZE_VALUE
        )
        ctx.browse_icon_size_reset_button = widgets.get(  # type: ignore[assignment]
            constants.BUTTON_BROWSE_ICON_SIZE_RESET
        )
        back_btn = widgets.get(constants.BUTTON_BROWSE_BACK)
        if back_btn is not None:
            back_btn.clicked.connect(lambda _=False, c=ctx: self._exit_folder_browse(c))
        if ctx.browse_icon_size_slider is not None:
            ctx.browse_icon_size_timer = QtCore.QTimer(ctx.page)
            ctx.browse_icon_size_timer.setSingleShot(True)
            ctx.browse_icon_size_timer.setInterval(
                constants.BROWSE_ICON_SIZE_LAYOUT_INTERVAL_MS
            )
            ctx.browse_icon_size_timer.timeout.connect(
                lambda c=ctx: self._apply_folder_icon_size_preview(c)
            )
            ctx.browse_icon_size_persist_timer = QtCore.QTimer(ctx.page)
            ctx.browse_icon_size_persist_timer.setSingleShot(True)
            ctx.browse_icon_size_persist_timer.setInterval(
                constants.BROWSE_ICON_SIZE_PERSIST_DEBOUNCE_MS
            )
            ctx.browse_icon_size_persist_timer.timeout.connect(
                lambda c=ctx: self._commit_folder_icon_size_change(c)
            )
            ctx.browse_icon_size_slider.valueChanged.connect(
                lambda value, c=ctx: self._schedule_folder_icon_size_change(c, value)
            )
            ctx.browse_icon_size_slider.sliderReleased.connect(
                lambda c=ctx: self._commit_folder_icon_size_change(c)
            )
        if ctx.browse_icon_size_reset_button is not None:
            ctx.browse_icon_size_reset_button.clicked.connect(
                lambda _=False, c=ctx: self._reset_folder_icon_size(c)
            )

        ctx.search_input.textChanged.connect(lambda _text, c=ctx: self.refresh_canvas(c))
        ctx.splitter.splitterMoved.connect(lambda _pos, _index, c=ctx: self._on_splitter_moved(c))

        ctx.canvas.entry_clicked.connect(
            lambda entry_id, c=ctx: self._on_entry_clicked(c, entry_id)
        )
        ctx.canvas.background_clicked.connect(lambda c=ctx: self._on_canvas_background_clicked(c))
        ctx.canvas.background_context_requested.connect(
            lambda canvas_pos, global_pos, c=ctx: self._show_canvas_background_context_menu(
                c, canvas_pos, global_pos
            )
        )
        ctx.canvas.area_selection_finished.connect(
            lambda entry_ids, additive, c=ctx: self._on_canvas_area_selection(
                c, entry_ids, additive
            )
        )
        ctx.canvas.entry_activated.connect(
            lambda entry_id, c=ctx: self._on_entry_activated(c, entry_id)
        )
        ctx.canvas.entry_context_requested.connect(
            lambda entry_id, pos, c=ctx: self._show_canvas_context_menu(c, entry_id, pos)
        )
        ctx.canvas.entry_moved.connect(
            lambda entry_id, x, y, c=ctx: self._on_entry_moved(c, entry_id, x, y)
        )
        ctx.canvas.entry_files_dropped.connect(
            lambda entry_id, payload, c=ctx: self._on_entry_files_dropped(
                c,
                entry_id,
                payload,
            )
        )

        for widget in (ctx.drop_zone, ctx.canvas.viewport(), ctx.canvas.surface):
            widget.setAcceptDrops(True)
            widget.installEventFilter(self)
            self._drop_widget_map[widget] = ctx

        if insert_position is None:
            insert_position = len(self.toolbox_tabs)
        insert_position = max(0, min(insert_position, len(self.toolbox_tabs)))
        self.toolbox_tabs.insert(insert_position, ctx)
        self._apply_tab_background_color(ctx)
        if rebuild_tabs:
            preferred_widget = ctx.page if switch_to else self.tab_widget.currentWidget()
            self._reinsert_fixed_tabs(preferred_widget=preferred_widget)
            self._refresh_tab_manager_ui(
                preferred_key=self._tab_manager_key_for_toolbox(ctx.tab_id)
            )
        return ctx

    def _toolbox_tab_index(self, ctx: ToolboxTabContext) -> int:
        try:
            return self.toolbox_tabs.index(ctx)
        except ValueError:
            return -1

    def _toolbox_context_for_index(self, tab_index: int) -> Optional[ToolboxTabContext]:
        if tab_index < 0:
            return None
        widget = self.tab_widget.widget(tab_index)
        if widget is None:
            return None
        return next((ctx for ctx in self.toolbox_tabs if ctx.page is widget), None)

    def current_toolbox_context(self) -> Optional[ToolboxTabContext]:
        return self._toolbox_context_for_index(self.tab_widget.currentIndex())

    def _load_toolbox_state(self) -> None:
        repository = getattr(self, "_state_repository", None)
        tabs = repository.snapshot() if repository is not None else load_toolbox_tabs(self.config_dir)
        if not tabs:
            tabs = [
                ToolboxTabData(
                    title=constants.DEFAULT_TOOLBOX_TAB_TITLE, entries=[], is_primary=True
                )
            ]
        self._normalize_primary_tabs(tabs)
        for tab_data in tabs:
            self._create_toolbox_tab(
                tab_data.title,
                tab_data.entries,
                tab_data.tab_id,
                tab_data.is_primary,
                tab_data.background_color,
                rebuild_tabs=False,
            )
        self._reinsert_fixed_tabs()
        self._refresh_tab_manager_ui()

    def _collect_toolbox_state(self) -> list[ToolboxTabData]:
        return [
            ToolboxTabData(
                title=ctx.title,
                entries=ctx.entries,
                tab_id=ctx.tab_id,
                is_primary=ctx.is_primary,
                background_color=ctx.background_color,
            )
            for ctx in self.toolbox_tabs
        ]

    def _on_splitter_moved(self, _ctx: ToolboxTabContext) -> None:
        self._save_settings()

    def persist_toolbox_state(self) -> None:
        current_state = self._collect_toolbox_state_dicts()
        repository = getattr(self, "_state_repository", None)
        if repository is not None:
            try:
                repository.replace(
                    current_state,
                    origin_window_id=getattr(self, "window_id", ""),
                    kind="view-command",
                    expected_revision=getattr(self, "_shared_state_revision", None),
                )
            except StaleToolboxStateError:
                self._apply_toolbox_state_dicts(repository.snapshot_dicts())
                self._shared_state_revision = repository.revision
                self.status.showMessage(
                    "Toolbox changed in another window; the stale local change was not applied.",
                    5000,
                )
                return
            self._undo_last_state = copy.deepcopy(current_state)
            if hasattr(self, "_update_managed_window_title"):
                self._update_managed_window_title()
            return
        self._record_undo_snapshot_before_persist(current_state)
        tabs = self._toolbox_state_from_dicts(current_state)
        self._normalize_primary_tabs(tabs)
        save_toolbox_tabs(self.config_dir, tabs)
        self._undo_last_state = copy.deepcopy(current_state)

    def _on_shared_toolbox_state_changed(self, change: object, state: object) -> None:
        if getattr(self, "_closing", False):
            return
        revision = int(getattr(change, "revision", 0))
        self._shared_state_revision = revision
        if (
            getattr(change, "origin_window_id", None) == getattr(self, "window_id", "")
            and getattr(change, "kind", "") == "view-command"
        ):
            return
        if not isinstance(state, list):
            return
        self._undo_suspended = True
        try:
            incoming = self._toolbox_state_from_dicts(state)
            can_update_in_place = len(incoming) == len(self.toolbox_tabs) and all(
                tab.tab_id == ctx.tab_id
                and tab.title == ctx.title
                and tab.is_primary == ctx.is_primary
                and self._normalize_tab_background_color(tab.background_color)
                == ctx.background_color
                for tab, ctx in zip(incoming, self.toolbox_tabs, strict=True)
            )
            if can_update_in_place:
                for tab, ctx in zip(incoming, self.toolbox_tabs, strict=True):
                    if [entry.to_dict() for entry in tab.entries] == [
                        entry.to_dict() for entry in ctx.entries
                    ]:
                        continue
                    ctx.entries = self._reconcile_entry_models(ctx.entries, tab.entries)
                    available_ids = {entry.entry_id for entry in ctx.entries}
                    ctx.selected_ids.intersection_update(available_ids)
                    if not ctx.browse_stack:
                        self.refresh_canvas(ctx)
                    if ctx is self.current_toolbox_context():
                        self._update_details(ctx)
                        self._update_action_buttons(ctx)
                        self._schedule_active_tab_size(ctx)
            else:
                self._apply_toolbox_state_dicts(state)
            self._undo_last_state = copy.deepcopy(state)
        finally:
            self._undo_suspended = False

    def _reinsert_fixed_tabs(self, preferred_widget: Optional[QtWidgets.QWidget] = None) -> None:
        if preferred_widget is None:
            preferred_widget = self.tab_widget.currentWidget()

        self.tab_widget.blockSignals(True)
        try:
            while self.tab_widget.count() > 0:
                self.tab_widget.removeTab(0)
            for ctx in self._visible_toolbox_tabs():
                self.tab_widget.addTab(ctx.page, ctx.title)
            self._install_new_toolbox_tab_action()

            self.tab_widget.addTab(self.settings_tab, self._settings_title)
            self.tab_widget.setTabVisible(self.tab_widget.indexOf(self.settings_tab), False)
            if not self._help_tab_hidden:
                self.tab_widget.addTab(self.help_tab, self._help_title)
                self.tab_widget.setTabVisible(self.tab_widget.indexOf(self.help_tab), False)

            # Build corner widget with QToolButtons (once only)
            if getattr(self, "_corner_widget", None) is None:
                corner_widget = QtWidgets.QWidget(self.tab_widget)
                corner_widget.setObjectName("corner_widget")
                corner_layout = QtWidgets.QHBoxLayout(corner_widget)
                corner_layout.setContentsMargins(0, 0, 0, 0)
                corner_layout.setSpacing(0)

                self._btn_settings = QtWidgets.QToolButton()
                self._btn_settings.setObjectName("corner_btn_settings")
                self._btn_settings.setAutoRaise(True)
                self._btn_settings.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
                self._btn_settings.clicked.connect(lambda: self._on_corner_btn_clicked(0))

                self._btn_help = QtWidgets.QToolButton()
                self._btn_help.setObjectName("corner_btn_help")
                self._btn_help.setAutoRaise(True)
                self._btn_help.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
                self._btn_help.clicked.connect(lambda: self._on_corner_btn_clicked(1))

                corner_layout.addWidget(self._btn_settings)
                corner_layout.addWidget(self._btn_help)

                self._corner_widget = corner_widget
                self.tab_widget.setCornerWidget(corner_widget, QtCore.Qt.Corner.TopRightCorner)
                self._apply_corner_button_style()

            # Update button labels and visibility
            self._btn_settings.setText(self._settings_title)
            self._btn_help.setText(self._help_title)
            self._btn_help.setVisible(not self._help_tab_hidden)
            self._update_corner_button_active_state(self.tab_widget.currentWidget())

            target_widget = preferred_widget
            if target_widget is None or self.tab_widget.indexOf(target_widget) < 0:
                target_widget = self.settings_tab
            target_index = self.tab_widget.indexOf(target_widget)
            if target_index >= 0:
                self.tab_widget.setCurrentIndex(target_index)
        finally:
            self.tab_widget.blockSignals(False)

    def _apply_corner_button_style(self) -> None:
        """Apply stylesheet to the corner buttons to match the main tab bar appearance."""
        tab_bar = self.tab_widget.tabBar()
        text = tab_bar.palette().color(QtGui.QPalette.ColorRole.WindowText).name()
        highlight = tab_bar.palette().color(QtGui.QPalette.ColorRole.Highlight).name()
        highlight_text = tab_bar.palette().color(QtGui.QPalette.ColorRole.HighlightedText).name()
        mid = tab_bar.palette().color(QtGui.QPalette.ColorRole.Mid).name()

        stylesheet = f"""
            QToolButton#corner_btn_settings,
            QToolButton#corner_btn_help {{
                color: {text};
                background: transparent;
                border: none;
                border-bottom: 2px solid transparent;
                padding: 4px 10px;
                margin: 0;
                font-size: 13px;
            }}
            QToolButton#corner_btn_settings:hover,
            QToolButton#corner_btn_help:hover {{
                background: rgba(128, 128, 128, 40);
                border-bottom: 2px solid {mid};
            }}
            QToolButton#corner_btn_settings[active=true],
            QToolButton#corner_btn_help[active=true] {{
                background: rgba(128, 128, 128, 30);
                border-bottom: 2px solid {highlight};
                color: {highlight_text if highlight_text != text else highlight};
            }}
        """
        self._corner_widget.setStyleSheet(stylesheet)

    def _update_corner_button_active_state(self, current_widget: QtWidgets.QWidget | None) -> None:
        """Highlight the correct corner button based on the active tab."""
        settings_active = current_widget is self.settings_tab
        help_active = current_widget is self.help_tab

        for btn, active in [
            (self._btn_settings, settings_active),
            (self._btn_help, help_active),
        ]:
            btn.setProperty("active", active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

    def _on_corner_btn_clicked(self, index: int) -> None:
        if index == 0:
            self.tab_widget.setCurrentWidget(self.settings_tab)
        elif index == 1 and not getattr(self, "_help_tab_hidden", False):
            self.tab_widget.setCurrentWidget(self.help_tab)

    # Keep old name as alias so _on_current_tab_changed still works
    def _on_corner_tab_clicked(self, index: int) -> None:
        self._on_corner_btn_clicked(index)

    def _install_new_toolbox_tab_action(self) -> None:
        """Insert the fixed browser-style plus action before Settings and Help."""

        index = self.tab_widget.addTab(self._new_toolbox_tab_action_page, "")
        self.tab_widget.setTabEnabled(index, False)
        self.tab_widget.setTabToolTip(index, "Create new toolbox tab (Ctrl+T)")

        button = QtWidgets.QToolButton(self.tab_widget.tabBar())
        button.setObjectName(constants.WIDGET_NEW_TOOLBOX_TAB_BUTTON)
        button.setText("+")
        button.setToolTip("Create new toolbox tab (Ctrl+T)")
        button.setAccessibleName("Create new toolbox tab")
        button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        button.setAutoRaise(True)
        button.setFixedSize(28, 28)
        font = button.font()
        font.setPixelSize(20)
        font.setBold(True)
        button.setFont(font)
        button.clicked.connect(self._create_new_toolbox_tab)
        self.tab_widget.tabBar().setTabButton(
            index,
            QtWidgets.QTabBar.ButtonPosition.RightSide,
            button,
        )
        self._new_toolbox_tab_button = button

    def _create_new_toolbox_tab(
        self,
        _checked: bool = False,
        *,
        insert_position: int | None = None,
    ) -> ToolboxTabContext:
        """Create, persist, and activate a new empty toolbox tab."""

        if (
            self.tab_widget.currentWidget() is self.settings_tab
            and bool(getattr(self, "_settings_dirty", False))
        ):
            self._apply_pending_settings()

        position = len(self.toolbox_tabs) if insert_position is None else insert_position
        ctx = self._create_toolbox_tab(
            title=self._suggest_toolbox_title(),
            entries=[],
            is_primary=False,
            insert_position=position,
            switch_to=True,
        )
        self.persist_toolbox_state()
        self._save_settings()
        self.refresh_all_canvases()
        self.status.showMessage(f"New toolbox tab created: {ctx.title}", 3000)
        return ctx

    def _show_tab_context_menu(self, pos: QtCore.QPoint) -> None:
        tab_bar = self.tab_widget.tabBar()
        index = tab_bar.tabAt(pos)
        if index < 0:
            return
        widget = self.tab_widget.widget(index)
        if widget is self._new_toolbox_tab_action_page:
            return
        is_fixed_tab = widget is self.settings_tab or widget is self.help_tab
        menu = QtWidgets.QMenu(self)
        rename_action = menu.addAction("Rename Tab")
        delete_toolbox_action = None
        new_toolbox_action = None
        open_in_new_window_action = None
        ctx = self._toolbox_context_for_index(index)
        if not is_fixed_tab:
            new_toolbox_action = menu.addAction("Create New Toolbox Tab")
            if ctx is not None and getattr(self, "_managed", False):
                open_in_new_window_action = menu.addAction("Open This Tab in New Window")
            if ctx is not None and not ctx.is_primary:
                delete_toolbox_action = menu.addAction("Delete Tab")
        chosen = menu.exec(tab_bar.mapToGlobal(pos))
        if chosen == rename_action:
            self._rename_tab(index)
        elif new_toolbox_action is not None and chosen == new_toolbox_action:
            insert_position = len(self.toolbox_tabs)
            if ctx is not None:
                insert_position = self._toolbox_tab_index(ctx) + 1
            self._create_new_toolbox_tab(insert_position=insert_position)
        elif open_in_new_window_action is not None and chosen == open_in_new_window_action:
            manager = getattr(self, "_window_manager", None)
            if manager is not None and ctx is not None:
                manager.create_window(ctx.tab_id)
        elif delete_toolbox_action is not None and chosen == delete_toolbox_action:
            self._delete_toolbox_tab_by_index(index)

    def _delete_toolbox_tab_by_index(self, tab_index: int) -> None:
        widget = self.tab_widget.widget(tab_index)
        if widget is self.settings_tab or widget is self.help_tab:
            return

        ctx = next((item for item in self.toolbox_tabs if item.page is widget), None)
        if ctx is None:
            self.status.showMessage("Could not resolve tab context.", 3000)
            return
        self._delete_toolbox_tab(ctx)

    def _delete_toolbox_tab(self, ctx: ToolboxTabContext) -> None:
        if ctx.is_primary:
            self.status.showMessage("The original toolbox tab cannot be deleted.", 3000)
            return
        if len(self.toolbox_tabs) <= 1:
            self.status.showMessage("At least one toolbox tab must remain.", 3000)
            return

        answer = QtWidgets.QMessageBox.question(
            self,
            "Delete Tab",
            f"Do you really want to delete tab '{ctx.title}'?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        if answer != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        tab_index = self._toolbox_tab_index(ctx)
        if tab_index < 0:
            return

        if self._folder_icon_size_change_pending(ctx):
            self._commit_folder_icon_size_change(ctx)

        for widget in (ctx.drop_zone, ctx.canvas.viewport(), ctx.canvas.surface):
            self._drop_widget_map.pop(widget, None)
            widget.removeEventFilter(self)

        preferred_widget = self.tab_widget.currentWidget()
        if preferred_widget is ctx.page:
            preferred_widget = self.settings_tab
        self.toolbox_tabs.pop(tab_index)
        ctx.page.deleteLater()
        self._hidden_toolbox_tab_ids.discard(ctx.tab_id)
        self._reinsert_fixed_tabs(preferred_widget=preferred_widget)
        self._refresh_tab_manager_ui()
        self.persist_toolbox_state()
        self._save_settings()
        self.refresh_all_canvases()
        self.status.showMessage(f"Tab deleted: {ctx.title}", 3000)

    def _suggest_toolbox_title(self) -> str:
        existing = {ctx.title for ctx in self.toolbox_tabs}
        if constants.DEFAULT_TOOLBOX_TAB_TITLE not in existing:
            return constants.DEFAULT_TOOLBOX_TAB_TITLE
        counter = 2
        while True:
            candidate = f"{constants.DEFAULT_TOOLBOX_TAB_TITLE} {counter}"
            if candidate not in existing:
                return candidate
            counter += 1

    def _rename_tab(self, index: int) -> None:
        current_title = self.tab_widget.tabText(index)
        new_title, accepted = QtWidgets.QInputDialog.getText(
            self, "Rename Tab", "New title:", text=current_title
        )
        new_title = new_title.strip()
        if not accepted or not new_title:
            return
        preferred_widget = self.tab_widget.currentWidget()
        ctx = self._toolbox_context_for_index(index)
        if ctx is not None:
            ctx.title = new_title
            preferred_widget = ctx.page
            self.persist_toolbox_state()
        elif self.tab_widget.widget(index) is self.settings_tab:
            self._settings_title = new_title
            preferred_widget = self.settings_tab
        elif self.tab_widget.widget(index) is self.help_tab:
            self._help_title = new_title
            preferred_widget = self.help_tab
        self._reinsert_fixed_tabs(preferred_widget=preferred_widget)
        self._refresh_tab_manager_ui(preferred_key=self._selected_tab_manager_key())
        self._refresh_section_color_manager()
        self._save_settings()
