#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canvas item widgets (tools and sections) for the toolbox canvas."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from app import constants
from app.canvas.layout_engine import build_section_metrics, build_tile_metrics
from app.domain.models import ToolboxEntry


class CanvasItemBase(QtWidgets.QFrame):
    clicked = QtCore.Signal(str)
    double_clicked = QtCore.Signal(str)
    context_requested = QtCore.Signal(str, QtCore.QPoint)
    move_finished = QtCore.Signal(str, int, int)
    move_live = QtCore.Signal()

    def __init__(self, entry: ToolboxEntry, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.entry = entry
        self._drag_active = False
        self._did_drag = False
        self._press_offset = QtCore.QPoint()
        self._drag_timer = QtCore.QTimer(self)
        self._drag_timer.setSingleShot(True)
        self._drag_timer.setInterval(constants.MOVE_HOLD_DELAY_MS)
        self._drag_timer.timeout.connect(self._activate_drag)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def _activate_drag(self) -> None:
        if QtWidgets.QApplication.mouseButtons() & QtCore.Qt.MouseButton.LeftButton:
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


class ToolTileWidget(CanvasItemBase):
    def __init__(
        self, entry: ToolboxEntry, icon: QtGui.QIcon, icon_size: int, parent=None
    ) -> None:
        super().__init__(entry, parent)
        self._icon = icon
        self._metrics = build_tile_metrics(icon_size)
        self._frame_enabled = constants.DEFAULT_TILE_FRAME_ENABLED
        self._frame_thickness = constants.DEFAULT_TILE_FRAME_THICKNESS
        self._frame_color = constants.DEFAULT_TILE_FRAME_COLOR
        self._highlight_color = constants.DEFAULT_TILE_HIGHLIGHT_COLOR
        self.setObjectName("tool_tile")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_Hover, True)
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setLineWidth(0)

        self._layout = QtWidgets.QVBoxLayout(self)
        self._layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.icon_label = QtWidgets.QLabel()
        self.icon_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self.icon_label, 0, QtCore.Qt.AlignmentFlag.AlignCenter)

        self.title_label = QtWidgets.QLabel(entry.title)
        self.title_label.setObjectName("tool_title")
        self.title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        self._layout.addWidget(self.title_label)
        self.set_icon_size(icon_size)

    @staticmethod
    def calculate_tile_size(icon_size: int) -> QtCore.QSize:
        return build_tile_metrics(icon_size).tile_size

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
            QLabel#tool_title {{
                font-weight: 600;
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

    def set_icon_size(self, icon_size: int) -> None:
        self._metrics = build_tile_metrics(icon_size)
        self._apply_style()
        self._layout.setContentsMargins(
            self._metrics.horizontal_padding,
            self._metrics.vertical_padding,
            self._metrics.horizontal_padding,
            self._metrics.vertical_padding,
        )
        self._layout.setSpacing(self._metrics.content_spacing)

        title_font = self.title_label.font()
        title_font.setBold(True)
        title_font.setPixelSize(self._metrics.font_pixel_size)
        self.title_label.setFont(title_font)
        self.title_label.setFixedHeight(self._metrics.title_height)
        self.title_label.setToolTip(f"{self.entry.title}\n{self.entry.path}")

        self.icon_label.setFixedSize(self._metrics.icon_size, self._metrics.icon_size)
        self.icon_label.setPixmap(
            self._icon.pixmap(self._metrics.icon_size, self._metrics.icon_size)
        )
        self.resize(self._metrics.tile_size)


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
