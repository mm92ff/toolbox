#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canvas item widgets (tools and sections) for the toolbox canvas."""

from __future__ import annotations

from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from app import constants
from app.canvas.layout_engine import build_section_metrics, build_tile_metrics
from app.domain.models import ToolboxEntry
from app.services.desktop_entries import (
    DesktopEntryError,
    DesktopLaunchInput,
    DesktopLaunchItem,
    desktop_entry_file_field_code,
    read_desktop_entry,
    validate_desktop_launch_input,
)
from app.services.folder_count import FolderCountService


class ElidedTitleLabel(QtWidgets.QLabel):
    """A label that supports multi-line text wrapping with eliding on the last line."""

    def __init__(self, text: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(text, parent)
        self.setToolTip(text)
        self.setWordWrap(True)

    def setText(self, text: str) -> None:
        super().setText(text)
        self.setToolTip(text)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        metrics = self.fontMetrics()
        rect = self.rect()

        option = QtGui.QTextOption()
        option.setWrapMode(QtGui.QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        option.setAlignment(self.alignment())

        layout = QtGui.QTextLayout(self.text(), self.font())
        layout.setTextOption(option)
        layout.beginLayout()

        y = 0
        line_count = 0
        max_lines = 2

        while True:
            line = layout.createLine()
            if not line.isValid():
                break

            line.setLineWidth(rect.width())

            if line_count == max_lines - 1:
                remaining_text = self.text()[line.textStart():]
                elided_string = metrics.elidedText(remaining_text, QtCore.Qt.TextElideMode.ElideRight, rect.width())
                painter.drawText(QtCore.QRect(0, int(y), rect.width(), metrics.lineSpacing()), int(self.alignment()), elided_string)
                break
            else:
                line.draw(painter, QtCore.QPointF(0, y))

            y += metrics.lineSpacing()
            line_count += 1

        layout.endLayout()


class RoundedIconLabel(QtWidgets.QLabel):
    """A label that draws its pixmap with rounded corners."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._radius = 0

    def set_radius(self, radius: int) -> None:
        self._radius = max(0, radius)
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        pixmap = self.pixmap()
        if not pixmap or pixmap.isNull():
            super().paintEvent(event)
            return

        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        # Calculate alignment (centered)
        x = (self.width() - pixmap.width()) // 2
        y = (self.height() - pixmap.height()) // 2

        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(x, y, pixmap.width(), pixmap.height()), self._radius, self._radius)

        painter.setClipPath(path)
        painter.drawPixmap(x, y, pixmap)



class CanvasItemBase(QtWidgets.QFrame):
    clicked = QtCore.Signal(str)
    double_clicked = QtCore.Signal(str)
    context_requested = QtCore.Signal(str, QtCore.QPoint)
    move_finished = QtCore.Signal(str, int, int)
    move_live = QtCore.Signal()
    hover_started = QtCore.Signal(str, QtCore.QPoint)
    hover_ended = QtCore.Signal(str)
    movement_blocked = QtCore.Signal(str)

    def __init__(self, entry: ToolboxEntry, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.entry = entry
        self._drag_active = False
        self._did_drag = False
        self._press_offset = QtCore.QPoint()
        self._last_release_parent_pos = QtCore.QPoint(-1, -1)
        self._drag_timer = QtCore.QTimer(self)
        self._drag_timer.setSingleShot(True)
        self._drag_timer.setInterval(constants.MOVE_HOLD_DELAY_MS)
        self._drag_timer.timeout.connect(self._activate_drag)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self._show_tooltips = constants.DEFAULT_SHOW_TOOLTIPS
        self._movement_enabled = True

    def set_movement_enabled(self, enabled: bool) -> None:
        self._movement_enabled = bool(enabled)
        if not self._movement_enabled:
            self._drag_timer.stop()
            self._drag_active = False

    def movement_enabled(self) -> bool:
        return self._movement_enabled

    def set_show_tooltips(self, show: bool) -> None:
        self._show_tooltips = bool(show)
        self._update_tooltips()

    def _update_tooltips(self) -> None:
        pass

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def _activate_drag(self) -> None:
        if QtWidgets.QApplication.mouseButtons() & QtCore.Qt.MouseButton.LeftButton:
            if not self._movement_enabled:
                self.movement_blocked.emit(self.entry.entry_id)
                return
            self._drag_active = True
            self.raise_()
            self.setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._drag_active = False
            self._did_drag = False
            self._press_offset = event.position().toPoint()
            self._drag_timer.start()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._drag_active and (event.buttons() & QtCore.Qt.MouseButton.LeftButton):
            parent = self.parentWidget()
            if parent is None:
                return
            new_pos = self.mapToParent(event.position().toPoint() - self._press_offset)
            self.move(
                max(constants.CANVAS_PADDING, new_pos.x()),
                max(constants.CANVAS_PADDING, new_pos.y()),
            )
            self._did_drag = True
            self.move_live.emit()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        self._drag_timer.stop()
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            if self._drag_active and self._did_drag:
                self._last_release_parent_pos = self.mapToParent(event.position().toPoint())
                self.move_finished.emit(self.entry.entry_id, self.x(), self.y())
                event.accept()
            elif not self._did_drag:
                self.clicked.emit(self.entry.entry_id)
            self._drag_active = False
            self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent) -> None:
        self._drag_timer.stop()
        self._drag_active = False
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.entry.entry_id)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent) -> None:
        self.context_requested.emit(self.entry.entry_id, event.globalPos())
        event.accept()

    def last_release_parent_pos(self) -> QtCore.QPoint:
        return QtCore.QPoint(self._last_release_parent_pos)

    def enterEvent(self, event: QtGui.QEnterEvent) -> None:
        self.hover_started.emit(
            self.entry.entry_id,
            self.mapToGlobal(QtCore.QPoint(self.width(), max(0, self.height() // 6))),
        )
        super().enterEvent(event)

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        self.hover_ended.emit(self.entry.entry_id)
        super().leaveEvent(event)


class ToolTileWidget(CanvasItemBase):
    files_dropped = QtCore.Signal(str, object)

    def __init__(
        self,
        entry: ToolboxEntry,
        icon: QtGui.QIcon,
        icon_size: int,
        parent=None,
        folder_count_service: FolderCountService | None = None,
        tile_font_size: int | None = None,
    ) -> None:
        super().__init__(entry, parent)
        self._icon = icon
        self._metrics = build_tile_metrics(icon_size, tile_font_size)
        self._frame_enabled = constants.DEFAULT_TILE_FRAME_ENABLED
        self._frame_thickness = constants.DEFAULT_TILE_FRAME_THICKNESS
        self._frame_color = constants.DEFAULT_TILE_FRAME_COLOR
        self._highlight_color = constants.DEFAULT_TILE_HIGHLIGHT_COLOR
        self.setObjectName("tool_tile")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_Hover, True)
        self.setAcceptDrops(True)
        self.setProperty("external_drop_state", "none")
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setLineWidth(0)
        self._overlay_mode = False

        self._layout = QtWidgets.QGridLayout(self)

        self.icon_label = RoundedIconLabel()
        self.icon_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.title_label = ElidedTitleLabel(entry.custom_title or entry.title)
        self.title_label.setObjectName("tool_title")
        self.title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)

        # Second line label for folder file count (hidden by default)
        self.file_count_label = QtWidgets.QLabel("")
        self.file_count_label.setObjectName("tool_file_count")
        self.file_count_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.file_count_label.hide()
        self._folder_count_mode = False
        self._pending_file_count_path: str | None = None
        self._folder_count_service = folder_count_service
        if self._folder_count_service is not None:
            self._folder_count_service.result_ready.connect(self._on_file_count_ready)
        self.set_icon_size(icon_size, tile_font_size)

    @staticmethod
    def calculate_tile_size(
        icon_size: int,
        tile_font_size: int | None = None,
    ) -> QtCore.QSize:
        return build_tile_metrics(icon_size, tile_font_size).tile_size

    def _apply_style(self) -> None:
        frame_color = QtGui.QColor(self._frame_color)
        if not frame_color.isValid():
            frame_color = QtGui.QColor(constants.DEFAULT_TILE_FRAME_COLOR)
        highlight_color = QtGui.QColor(self._highlight_color)
        if not highlight_color.isValid():
            highlight_color = QtGui.QColor(constants.DEFAULT_TILE_HIGHLIGHT_COLOR)

        base_border_width = max(0, self._frame_thickness if self._frame_enabled else 0)
        base_border_color = frame_color.name() if base_border_width else "transparent"
        base_fill_rgba = f"rgba(255, 255, 255, {constants.DEFAULT_TILE_BASE_FILL_ALPHA})"
        hover_fill_rgba = (
            f"rgba({highlight_color.red()}, {highlight_color.green()}, "
            f"{highlight_color.blue()}, {constants.DEFAULT_TILE_HOVER_ALPHA})"
        )
        selected_fill_rgba = (
            f"rgba({highlight_color.red()}, {highlight_color.green()}, "
            f"{highlight_color.blue()}, {constants.DEFAULT_TILE_SELECTED_ALPHA})"
        )
        highlight_line_color = highlight_color.name()
        hover_border_width = max(1, base_border_width) if self._frame_enabled else 0
        selected_border_width = max(2, base_border_width + 1) if self._frame_enabled else 0

        self.setStyleSheet(f"""
            QFrame#tool_tile {{
                border: {base_border_width}px solid {base_border_color};
                border-radius: {self._metrics.border_radius}px;
                background: {base_fill_rgba};
            }}
            QFrame#tool_tile[hovered=\"true\"] {{
                border: {hover_border_width}px solid {highlight_line_color};
                background: {hover_fill_rgba};
            }}
            QFrame#tool_tile[selected=\"true\"] {{
                border: {selected_border_width}px solid {highlight_line_color};
                background: {selected_fill_rgba};
            }}
            QFrame#tool_tile[external_drop_state=\"valid\"] {{
                border: 2px solid #39b86a;
                background: rgba(57, 184, 106, 52);
            }}
            QFrame#tool_tile[external_drop_state=\"invalid\"] {{
                border: 2px solid #dc5a63;
                background: rgba(220, 90, 99, 52);
            }}
            QLabel#tool_title {{
                font-weight: 600;
                background: transparent;
            }}
            QLabel#tool_file_count {{
                background: transparent;
            }}
            """)

    def set_tile_style(
        self, frame_enabled: bool, frame_thickness: int, frame_color: str, highlight_color: str
    ) -> None:
        self._frame_enabled = bool(frame_enabled)
        self._frame_thickness = max(
            constants.MIN_TILE_FRAME_THICKNESS,
            min(constants.MAX_TILE_FRAME_THICKNESS, int(frame_thickness)),
        )
        self._frame_color = (frame_color or "").strip() or constants.DEFAULT_TILE_FRAME_COLOR
        self._highlight_color = (
            highlight_color or ""
        ).strip() or constants.DEFAULT_TILE_HIGHLIGHT_COLOR
        self._apply_style()

    def _set_hovered(self, hovered: bool) -> None:
        if bool(self.property("hovered")) == hovered:
            return
        self.setProperty("hovered", hovered)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def enterEvent(self, event: QtGui.QEnterEvent) -> None:
        self._set_hovered(True)
        super().enterEvent(event)

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        self._set_hovered(False)
        super().leaveEvent(event)

    def set_overlay_mode(self, enabled: bool) -> None:
        self._overlay_mode = enabled
        # This will be visually applied the next time set_icon_size is called
        # which surface_render does immediately after.

    def set_folder_file_count_mode(self, enabled: bool) -> None:
        """Show folder name on line 1 and file count on line 2 when enabled."""
        import os
        path = self.entry.path
        is_folder = bool(path) and os.path.isdir(path)
        self._folder_count_mode = enabled and is_folder

        if self._folder_count_mode:
            display_name = self.entry.custom_title or self.entry.title
            self._pending_file_count_path = path

            # Line 1: folder name, single-line with elision
            self.title_label.setWordWrap(False)
            self.title_label.setText(display_name)

            # Line 2: placeholder until worker finishes
            self.file_count_label.setText("...")

            if self._folder_count_service is not None:
                normalized = str(Path(path).expanduser().resolve(strict=False))
                self._pending_file_count_path = normalized
                self._folder_count_service.request(normalized)
            else:
                self.file_count_label.setText("–")
        else:
            self._pending_file_count_path = None
            self._folder_count_mode = False

            # Restore normal single label layout
            self.title_label.setWordWrap(True)
            self.title_label.setText(self.entry.custom_title or self.entry.title)

            self.file_count_label.setText("")

    @QtCore.Slot(str, int, str)
    def _on_file_count_ready(self, path: str, count: int, error: str) -> None:
        if getattr(self, "_pending_file_count_path", None) == path:
            if error:
                self.file_count_label.setText("–")
                self.file_count_label.setToolTip(error)
            else:
                suffix = "1 Element" if count == 1 else f"{count} Elemente"
                self.file_count_label.setText(suffix)
                self.file_count_label.setToolTip("")


    def set_icon_size(
        self,
        icon_size: int,
        tile_font_size: int | None = None,
    ) -> None:
        self._metrics = build_tile_metrics(icon_size, tile_font_size)
        self._apply_style()
        
        if self._overlay_mode:
            self._layout.setContentsMargins(0, 0, 0, 0)
            self._layout.setSpacing(0)
            self._layout.removeWidget(self.title_label)
            self._layout.removeWidget(self.file_count_label)
            self.title_label.setParent(self.icon_label)
            self.file_count_label.setParent(self)
            self.file_count_label.hide()
            self._layout.addWidget(self.icon_label, 0, 0, 2, 1, QtCore.Qt.AlignmentFlag.AlignCenter)
            self.title_label.setStyleSheet(f"background: rgba(0, 0, 0, 170); color: white; border-bottom-left-radius: {self._metrics.border_radius}px; border-bottom-right-radius: {self._metrics.border_radius}px; padding-top: 4px; padding-bottom: 4px;")
            self.title_label.show()
        else:
            self.title_label.setParent(self)
            self.file_count_label.setParent(self)
            self._layout.setContentsMargins(
                self._metrics.horizontal_padding,
                self._metrics.vertical_padding,
                self._metrics.horizontal_padding,
                self._metrics.vertical_padding,
            )
            self._layout.setSpacing(0)
            self._layout.addWidget(self.icon_label, 0, 0, 1, 1, QtCore.Qt.AlignmentFlag.AlignCenter)
            if self._folder_count_mode:
                # Split title_height evenly between name (line1) and count (line2)
                half_h = self._metrics.title_height // 2
                self.title_label.setFixedHeight(half_h)
                self.file_count_label.setFixedHeight(self._metrics.title_height - half_h)
                self._layout.addWidget(self.title_label, 1, 0, 1, 1, QtCore.Qt.AlignmentFlag.AlignCenter)
                self._layout.addWidget(self.file_count_label, 2, 0, 1, 1, QtCore.Qt.AlignmentFlag.AlignCenter)
                self.file_count_label.show()
            else:
                self._layout.addWidget(self.title_label, 1, 0, 1, 1, QtCore.Qt.AlignmentFlag.AlignCenter)
                self.file_count_label.hide()
            self.title_label.setStyleSheet("background: transparent;")
            self.title_label.show()

        title_font = self.title_label.font()
        title_font.setBold(True)
        title_font.setPixelSize(self._metrics.font_pixel_size)
        self.title_label.setFont(title_font)
        # In folder_count_mode heights are already split above; only set here for normal/overlay mode
        if not self._folder_count_mode:
            self.title_label.setFixedHeight(self._metrics.title_height)

        # Apply same font to file_count_label (slightly smaller)
        count_font = self.file_count_label.font()
        count_font.setPixelSize(max(8, self._metrics.font_pixel_size - 1))
        self.file_count_label.setFont(count_font)
        if self._overlay_mode:
            self.title_label.setGeometry(
                0,
                self._metrics.tile_size.height() - self._metrics.title_height,
                self._metrics.tile_size.width(),
                self._metrics.title_height
            )
        
        tooltip = f"{self.entry.title}\n{self.entry.path}"
        if self.entry.path.lower().endswith(".desktop"):
            try:
                field_code = desktop_entry_file_field_code(
                    read_desktop_entry(self.entry.path)
                )
            except DesktopEntryError:
                field_code = ""
            if field_code:
                tooltip += f"\nDrop files or URLs here (%{field_code})"

        self._current_tooltip = tooltip
        self._update_tooltips()

    def _update_tooltips(self) -> None:
        tooltip = getattr(self, "_current_tooltip", "")
        if getattr(self, "_show_tooltips", True) and tooltip:
            self.title_label.setToolTip(tooltip)
            self.setToolTip(tooltip)
        else:
            self.title_label.setToolTip("")
            self.setToolTip("")

        if self._overlay_mode:
            target_size = self._metrics.tile_size.width()
            self.icon_label.setFixedSize(self._metrics.tile_size)
            self.icon_label.set_radius(self._metrics.border_radius)
            self.icon_label.setPixmap(
                self._icon.pixmap(target_size, target_size)
            )
        else:
            self.icon_label.setFixedSize(self._metrics.icon_size, self._metrics.icon_size)
            self.icon_label.set_radius(max(0, self._metrics.border_radius - 4))
            self.icon_label.setPixmap(
                self._icon.pixmap(self._metrics.icon_size, self._metrics.icon_size)
            )
        self.resize(self._metrics.tile_size)

    def set_icon(self, icon: QtGui.QIcon) -> None:
        self._icon = icon
        target_size = self._metrics.tile_size.width() if self._overlay_mode else self._metrics.icon_size
        self.icon_label.setPixmap(
            self._icon.pixmap(target_size, target_size)
        )

    def _set_external_drop_state(self, state: str) -> None:
        normalized = state if state in {"none", "valid", "invalid"} else "none"
        if str(self.property("external_drop_state") or "none") == normalized:
            return
        self.setProperty("external_drop_state", normalized)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def _drop_is_compatible(self, urls: list[QtCore.QUrl]) -> bool:
        if not urls or not self.entry.path.lower().endswith(".desktop"):
            return False
        try:
            metadata = read_desktop_entry(self.entry.path)
            field_code = desktop_entry_file_field_code(metadata)
            if not field_code:
                return False

            mime_database = QtCore.QMimeDatabase()
            launch_items: list[DesktopLaunchItem] = []
            for url in urls:
                local_path = url.toLocalFile()
                mime_type = ""
                if local_path:
                    path = QtCore.QFileInfo(local_path)
                    mime_type = (
                        "inode/directory"
                        if path.isDir()
                        else mime_database.mimeTypeForFile(local_path).name()
                    )
                launch_items.append(
                    DesktopLaunchItem(
                        url=url.toString(
                            QtCore.QUrl.ComponentFormattingOption.FullyEncoded
                        ),
                        local_path=local_path,
                        mime_type=mime_type,
                    )
                )
            validate_desktop_launch_input(
                metadata,
                DesktopLaunchInput(tuple(launch_items)),
            )
            return True
        except DesktopEntryError:
            return False

    def dragEnterEvent(self, event: QtGui.QDragEnterEvent) -> None:
        mime_data = event.mimeData()
        if not mime_data.hasUrls():
            self._set_external_drop_state("none")
            event.ignore()
            return
        urls = list(mime_data.urls())
        self._set_external_drop_state(
            "valid" if self._drop_is_compatible(urls) else "invalid"
        )
        # Accept invalid URL drops as well so the controller can explain why
        # the selected tile cannot consume them instead of adding a new tile.
        event.acceptProposedAction()

    def dragLeaveEvent(self, event: QtGui.QDragLeaveEvent) -> None:
        self._set_external_drop_state("none")
        event.accept()

    def dropEvent(self, event: QtGui.QDropEvent) -> None:
        mime_data = event.mimeData()
        urls = list(mime_data.urls()) if mime_data.hasUrls() else []
        payload = tuple(
            {
                "url": url.toString(
                    QtCore.QUrl.ComponentFormattingOption.FullyEncoded
                ),
                "local_path": url.toLocalFile(),
            }
            for url in urls
        )
        self._set_external_drop_state("none")
        if not payload:
            event.ignore()
            return
        self.files_dropped.emit(self.entry.entry_id, payload)
        event.acceptProposedAction()


class SectionWidget(CanvasItemBase):
    def __init__(
        self,
        entry: ToolboxEntry,
        title_font_size: int,
        line_thickness: int,
        line_color: str,
        title_color: str,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(entry, parent)
        self.setCursor(QtCore.Qt.CursorShape.SizeVerCursor)
        self.setObjectName("section_widget")
        self._metrics = build_section_metrics(title_font_size, line_thickness)
        self._line_color = line_color
        self._title_color = title_color

        self._layout = QtWidgets.QHBoxLayout(self)
        self.left_line = QtWidgets.QFrame()
        self.left_line.setObjectName("section_line")
        self.left_line.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self._layout.addWidget(self.left_line, 1)

        self.title_label = QtWidgets.QLabel(entry.title)
        self.title_label.setObjectName("section_title")
        self.title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self.title_label, 0)

        self.right_line = QtWidgets.QFrame()
        self.right_line.setObjectName("section_line")
        self.right_line.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self._layout.addWidget(self.right_line, 1)
        self.set_section_style(title_font_size, line_thickness, line_color, title_color)

    @property
    def section_height(self) -> int:
        return self._metrics.height

    def set_selected(self, selected: bool) -> None:
        super().set_selected(selected)
        self._apply_style()

    def set_drop_hint(self, state: bool | str) -> None:
        if isinstance(state, str):
            normalized_state = state.strip().lower()
            if normalized_state not in {"none", "snap", "conflict"}:
                normalized_state = "none"
        else:
            normalized_state = "snap" if state else "none"

        self.setProperty("drop_hint_state", normalized_state)
        # Keep legacy boolean property for compatibility with existing checks/tests.
        self.setProperty("drop_hint", normalized_state != "none")
        self._apply_style()

    def set_section_style(
        self, title_font_size: int, line_thickness: int, line_color: str, title_color: str = ""
    ) -> None:
        self._metrics = build_section_metrics(title_font_size, line_thickness)
        self._line_color = line_color
        self._title_color = (title_color or "").strip()
        self._layout.setContentsMargins(
            0, self._metrics.vertical_padding, 0, self._metrics.vertical_padding
        )
        self._layout.setSpacing(self._metrics.horizontal_spacing)

        font = self.title_label.font()
        font.setBold(True)
        font.setPixelSize(self._metrics.font_pixel_size)
        self.title_label.setFont(font)
        self.title_label.setContentsMargins(
            self._metrics.title_horizontal_padding, 0, self._metrics.title_horizontal_padding, 0
        )

        self.left_line.setFixedHeight(self._metrics.line_thickness)
        self.right_line.setFixedHeight(self._metrics.line_thickness)
        self._apply_style()
        self.resize(max(self.width(), 480), self._metrics.height)

    def _apply_style(self) -> None:
        color = QtGui.QColor(self._line_color)
        if not color.isValid():
            color = QtGui.QColor(constants.DEFAULT_SECTION_LINE_COLOR)
        line_color = color.name()
        hint_state = str(self.property("drop_hint_state") or "").strip().lower()
        if not hint_state:
            hint_state = "snap" if bool(self.property("drop_hint")) else "none"

        if hint_state == "conflict":
            line_color = "#e74c3c"
            title_color = line_color
        elif hint_state == "snap":
            line_color = "#2ecc71"
            title_color = line_color
        elif bool(self.property("selected")):
            title_color = self.palette().color(QtGui.QPalette.ColorRole.Highlight).name()
        else:
            configured_title_color = QtGui.QColor(self._title_color)
            if configured_title_color.isValid():
                title_color = configured_title_color.name()
            else:
                title_color = self.palette().color(QtGui.QPalette.ColorRole.Text).name()
        self.setStyleSheet(f"""
            QFrame#section_widget {{
                background: transparent;
                border: none;
            }}
            QLabel#section_title {{
                color: {title_color};
                font-weight: 700;
            }}
            QFrame#section_line {{
                background: {line_color};
                border-radius: {max(1, self._metrics.line_thickness // 2)}px;
            }}
            """)
