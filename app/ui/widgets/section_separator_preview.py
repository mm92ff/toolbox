#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Live preview widget for section separator settings."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from app import constants
from app.canvas.layout_engine import build_section_metrics


class SectionSeparatorLivePreview(QtWidgets.QWidget):
    """Visual preview for section header size, line thickness, gaps, and line color."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName(constants.WIDGET_SECTION_SEPARATOR_LIVE_PREVIEW)
        self._font_size = constants.DEFAULT_SECTION_FONT_SIZE
        self._line_thickness = constants.DEFAULT_SECTION_LINE_THICKNESS
        self._line_color = constants.DEFAULT_SECTION_LINE_COLOR
        self._gap_above = constants.DEFAULT_SECTION_PROTECTED_GAP_ABOVE
        self._gap_below = constants.DEFAULT_SECTION_PROTECTED_GAP_BELOW
        self._title = "Section Title"
        self.setMinimumHeight(124)

    def update_preview(
        self,
        *,
        font_size: int,
        line_thickness: int,
        line_color: str,
        gap_above: int,
        gap_below: int,
    ) -> None:
        self._font_size = int(font_size)
        self._line_thickness = int(line_thickness)
        self._line_color = (line_color or "").strip() or constants.DEFAULT_SECTION_LINE_COLOR
        self._gap_above = max(0, int(gap_above))
        self._gap_below = max(0, int(gap_below))
        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QtCore.QSize:
        metrics = build_section_metrics(self._font_size, self._line_thickness)
        visual_gap_above = max(28, self._gap_above + 12)
        visual_gap_below = max(28, self._gap_below + 12)
        total_height = (
            visual_gap_above
            + metrics.height
            + visual_gap_below
            + 36
        )
        return QtCore.QSize(420, max(124, total_height))

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)

        rect = self.rect().adjusted(4, 4, -4, -4)
        metrics = build_section_metrics(self._font_size, self._line_thickness)
        line_color = QtGui.QColor(self._line_color)
        if not line_color.isValid():
            line_color = QtGui.QColor(constants.DEFAULT_SECTION_LINE_COLOR)
        title_color = self.palette().color(QtGui.QPalette.ColorRole.Text)
        zone_border = self.palette().color(QtGui.QPalette.ColorRole.Mid)
        zone_fill = self.palette().color(QtGui.QPalette.ColorRole.Base).lighter(106)
        container_fill = self.palette().color(QtGui.QPalette.ColorRole.Base).lighter(103)
        container_border = self.palette().color(QtGui.QPalette.ColorRole.Dark)

        # Keep a comfortably large visual zone so labels remain readable.
        top_zone_h = max(28, self._gap_above + 12)
        bottom_zone_h = max(28, self._gap_below + 12)
        header_top = rect.top() + top_zone_h
        header_h = metrics.height
        header_mid = header_top + (header_h // 2)

        top_zone = QtCore.QRect(rect.left(), rect.top(), rect.width(), top_zone_h)
        bottom_zone = QtCore.QRect(
            rect.left(),
            header_top + header_h,
            rect.width(),
            max(8, min(bottom_zone_h, max(8, rect.bottom() - (header_top + header_h) + 1))),
        )

        container_path = QtGui.QPainterPath()
        container_path.addRoundedRect(QtCore.QRectF(rect), 8, 8)
        painter.fillPath(container_path, container_fill)
        painter.setPen(QtGui.QPen(container_border, 1))
        painter.drawPath(container_path)

        painter.fillRect(top_zone, zone_fill)
        painter.fillRect(bottom_zone, zone_fill)
        zone_pen = QtGui.QPen(zone_border, 1)
        painter.setPen(zone_pen)
        painter.drawRect(top_zone.adjusted(0, 0, -1, -1))
        painter.drawRect(bottom_zone.adjusted(0, 0, -1, -1))

        font = painter.font()
        font.setBold(True)
        font.setPixelSize(metrics.font_pixel_size)
        painter.setFont(font)
        title_metrics = QtGui.QFontMetrics(font)
        title_w = title_metrics.horizontalAdvance(self._title)
        title_pad = metrics.title_horizontal_padding
        title_total_w = title_w + (2 * title_pad)
        title_total_w = min(title_total_w, max(60, rect.width() - 40))
        title_rect = QtCore.QRect(
            rect.center().x() - (title_total_w // 2),
            header_mid - (title_metrics.height() // 2),
            title_total_w,
            title_metrics.height(),
        )

        pen = QtGui.QPen(line_color, metrics.line_thickness)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        left_start = QtCore.QPointF(rect.left() + 8, header_mid)
        left_end = QtCore.QPointF(title_rect.left() - metrics.horizontal_spacing, header_mid)
        right_start = QtCore.QPointF(title_rect.right() + metrics.horizontal_spacing, header_mid)
        right_end = QtCore.QPointF(rect.right() - 8, header_mid)
        if left_end.x() > left_start.x():
            painter.drawLine(left_start, left_end)
        if right_end.x() > right_start.x():
            painter.drawLine(right_start, right_end)

        painter.setPen(title_color)
        painter.drawText(title_rect, QtCore.Qt.AlignmentFlag.AlignCenter, self._title)

        badge_bg = self.palette().color(QtGui.QPalette.ColorRole.Window)
        badge_border = self.palette().color(QtGui.QPalette.ColorRole.Midlight)
        badge_text = self.palette().color(QtGui.QPalette.ColorRole.Text)
        badge_font = painter.font()
        badge_font.setBold(True)
        badge_font.setPixelSize(max(10, min(13, metrics.font_pixel_size - 2)))
        badge_metrics = QtGui.QFontMetrics(badge_font)

        def draw_badge(zone_rect: QtCore.QRect, text: str) -> None:
            if zone_rect.height() <= 0 or zone_rect.width() <= 0:
                return
            badge_h = max(18, badge_metrics.height() + 6)
            badge_h = min(badge_h, max(16, zone_rect.height() - 4))
            badge_w = min(
                zone_rect.width() - 12,
                max(110, badge_metrics.horizontalAdvance(text) + 18),
            )
            badge_x = zone_rect.left() + 8
            badge_y = zone_rect.top() + max(2, (zone_rect.height() - badge_h) // 2)
            badge_rect = QtCore.QRect(badge_x, badge_y, badge_w, badge_h)

            badge_path = QtGui.QPainterPath()
            badge_path.addRoundedRect(QtCore.QRectF(badge_rect), 6, 6)
            painter.fillPath(badge_path, badge_bg)
            painter.setPen(QtGui.QPen(badge_border, 1))
            painter.drawPath(badge_path)

            painter.setFont(badge_font)
            painter.setPen(badge_text)
            painter.drawText(
                badge_rect.adjusted(8, 0, -8, 0),
                QtCore.Qt.AlignmentFlag.AlignVCenter | QtCore.Qt.AlignmentFlag.AlignLeft,
                text,
            )

        draw_badge(top_zone, f"Gap Above {self._gap_above}px")
        draw_badge(bottom_zone, f"Gap Below {self._gap_below}px")
