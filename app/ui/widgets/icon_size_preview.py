#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compact live preview widget for icon-size changes in settings."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from app import constants
from app.canvas.layout_engine import build_tile_metrics


class _PreviewGridContainer(QtWidgets.QFrame):
    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("icon_preview_grid_container")
        self._background = QtGui.QColor(constants.DEFAULT_ICON_PREVIEW_BACKGROUND_COLOR)
        self._spacing_x = constants.DEFAULT_GRID_SPACING_X
        self._spacing_y = constants.DEFAULT_GRID_SPACING_Y

    def set_preview_background(self, color_value: str) -> None:
        color = QtGui.QColor((color_value or "").strip())
        if not color.isValid():
            color = QtGui.QColor(constants.DEFAULT_ICON_PREVIEW_BACKGROUND_COLOR)
        self._background = color
        self.update()

    def set_preview_spacing(self, spacing_x: int, spacing_y: int) -> None:
        self._spacing_x = max(0, int(spacing_x))
        self._spacing_y = max(0, int(spacing_y))
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QtGui.QPainter(self)
        try:
            painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
            rect = self.rect().adjusted(0, 0, -1, -1)

            path = QtGui.QPainterPath()
            path.addRoundedRect(QtCore.QRectF(rect), 8, 8)
            painter.fillPath(path, self._background)
            border = QtGui.QPen(self._background.lighter(160), 1)
            painter.setPen(border)
            painter.drawPath(path)

            pattern_pen = QtGui.QPen(self._background.darker(118), 1)
            pattern_pen.setStyle(QtCore.Qt.PenStyle.DotLine)
            painter.setPen(pattern_pen)
            step = 12
            for x in range(rect.left() + 6, rect.right(), step):
                painter.drawLine(x, rect.top() + 4, x, rect.bottom() - 4)

            tiles = sorted(
                self.findChildren(QtWidgets.QFrame, "icon_size_preview_tile"),
                key=lambda tile: (tile.y(), tile.x()),
            )
            if len(tiles) < 4:
                return

            top_row_y = min(tile.y() for tile in tiles)
            top_row = sorted([tile for tile in tiles if tile.y() == top_row_y], key=lambda tile: tile.x())
            bottom_row_y = max(tile.y() for tile in tiles)
            bottom_row = sorted(
                [tile for tile in tiles if tile.y() == bottom_row_y], key=lambda tile: tile.x()
            )
            if len(top_row) < 2 or not bottom_row:
                return

            gap_brush = QtGui.QColor("#f1f5f9")
            gap_brush.setAlpha(90)
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(gap_brush)

            first = top_row[0].geometry()
            second = top_row[1].geometry()
            top = top_row[0].geometry()
            bottom = bottom_row[0].geometry()

            # Extend spacing visualization to the outer preview area and paint
            # both bands as one path so the center does not get double-alpha.
            content_rect = rect
            gap_path = QtGui.QPainterPath()
            gap_path.setFillRule(QtCore.Qt.FillRule.WindingFill)

            gap_x = first.right() + 1
            gap_w = max(2, second.left() - gap_x)
            if gap_w > 1 and self._spacing_x > 0:
                v_gap_rect = QtCore.QRect(
                    gap_x,
                    content_rect.top(),
                    gap_w,
                    content_rect.height(),
                )
                gap_path.addRect(QtCore.QRectF(v_gap_rect))

            gap_y = top.bottom() + 1
            gap_h = max(2, bottom.top() - gap_y)
            if gap_h > 1 and self._spacing_y > 0:
                h_gap_rect = QtCore.QRect(
                    content_rect.left(),
                    gap_y,
                    content_rect.width(),
                    gap_h,
                )
                gap_path.addRect(QtCore.QRectF(h_gap_rect))

            if not gap_path.isEmpty():
                painter.fillPath(gap_path, gap_brush)
        finally:
            painter.end()


class _PreviewTile(QtWidgets.QFrame):
    def __init__(self, title: str, icon: QtGui.QIcon, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = title
        self._icon = icon
        self._metrics = build_tile_metrics(constants.DEFAULT_ICON_SIZE)
        self._frame_enabled = constants.DEFAULT_TILE_FRAME_ENABLED
        self._frame_thickness = constants.DEFAULT_TILE_FRAME_THICKNESS
        self._frame_color = constants.DEFAULT_TILE_FRAME_COLOR
        self._highlight_color = constants.DEFAULT_TILE_HIGHLIGHT_COLOR
        self.setObjectName("icon_size_preview_tile")
        self.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.setLineWidth(0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._layout = layout

        self.icon_label = QtWidgets.QLabel()
        self.icon_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.icon_label, 0, QtCore.Qt.AlignmentFlag.AlignCenter)

        self.title_label = QtWidgets.QLabel(title)
        self.title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        self.apply_style(
            icon_size=constants.DEFAULT_ICON_SIZE,
            frame_enabled=constants.DEFAULT_TILE_FRAME_ENABLED,
            frame_thickness=constants.DEFAULT_TILE_FRAME_THICKNESS,
            frame_color=constants.DEFAULT_TILE_FRAME_COLOR,
            highlight_color=constants.DEFAULT_TILE_HIGHLIGHT_COLOR,
        )

    def apply_style(
        self,
        *,
        icon_size: int,
        frame_enabled: bool,
        frame_thickness: int,
        frame_color: str,
        highlight_color: str,
    ) -> None:
        self._metrics = build_tile_metrics(icon_size)
        self._frame_enabled = bool(frame_enabled)
        self._frame_thickness = max(
            constants.MIN_TILE_FRAME_THICKNESS,
            min(constants.MAX_TILE_FRAME_THICKNESS, int(frame_thickness)),
        )
        self._frame_color = (frame_color or "").strip() or constants.DEFAULT_TILE_FRAME_COLOR
        self._highlight_color = (
            highlight_color or ""
        ).strip() or constants.DEFAULT_TILE_HIGHLIGHT_COLOR

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
        self.title_label.setToolTip(self._title)

        self.icon_label.setFixedSize(self._metrics.icon_size, self._metrics.icon_size)
        self.icon_label.setPixmap(self._icon.pixmap(self._metrics.icon_size, self._metrics.icon_size))
        self.setFixedSize(self._metrics.tile_size)

        frame = QtGui.QColor(self._frame_color)
        if not frame.isValid():
            frame = QtGui.QColor(constants.DEFAULT_TILE_FRAME_COLOR)
        highlight = QtGui.QColor(self._highlight_color)
        if not highlight.isValid():
            highlight = QtGui.QColor(constants.DEFAULT_TILE_HIGHLIGHT_COLOR)

        border_width = self._frame_thickness if self._frame_enabled else 0
        border_color = frame.name() if border_width else "transparent"
        fill_color = (
            f"rgba({highlight.red()}, {highlight.green()}, {highlight.blue()}, "
            f"{constants.DEFAULT_TILE_BASE_FILL_ALPHA})"
        )
        self.setStyleSheet(
            f"""
            QFrame#icon_size_preview_tile {{
                border: {border_width}px solid {border_color};
                border-radius: {self._metrics.border_radius}px;
                background: {fill_color};
            }}
            """
        )


class IconSizeLivePreview(QtWidgets.QWidget):
    """Simple non-interactive tile preview for icon size and grid spacing."""

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName(constants.WIDGET_ICON_SIZE_LIVE_PREVIEW)
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        hint = QtWidgets.QLabel(
            "Live preview (icon size + grid spacing, visual only)."
        )
        hint.setWordWrap(True)
        root.addWidget(hint)

        container_row = QtWidgets.QHBoxLayout()
        container_row.setSpacing(0)
        container_row.addStretch(1)
        self._grid_container = _PreviewGridContainer(self)
        self._grid_layout = QtWidgets.QGridLayout(self._grid_container)
        self._grid_layout.setContentsMargins(6, 6, 6, 6)
        self._grid_layout.setHorizontalSpacing(constants.DEFAULT_GRID_SPACING_X)
        self._grid_layout.setVerticalSpacing(constants.DEFAULT_GRID_SPACING_Y)
        self._tiles = [
            _PreviewTile(
                "App One",
                self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_ComputerIcon),
                self,
            ),
            _PreviewTile(
                "Folder Tool",
                self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DirIcon),
                self,
            ),
            _PreviewTile(
                "Script",
                self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_FileIcon),
                self,
            ),
            _PreviewTile(
                "Shortcut",
                self.style().standardIcon(QtWidgets.QStyle.StandardPixmap.SP_DirLinkIcon),
                self,
            ),
        ]
        positions = ((0, 0), (0, 1), (1, 0), (1, 1))
        for tile, (row, col) in zip(self._tiles, positions):
            self._grid_layout.addWidget(tile, row, col)
        container_row.addWidget(self._grid_container)
        container_row.addStretch(1)
        root.addLayout(container_row)
        self._apply_background_style(constants.DEFAULT_ICON_PREVIEW_BACKGROUND_COLOR)

    def _normalize_background_color(self, value: str) -> str:
        color = QtGui.QColor((value or "").strip())
        if not color.isValid():
            return constants.DEFAULT_ICON_PREVIEW_BACKGROUND_COLOR
        return color.name()

    def _apply_background_style(self, color_value: str) -> None:
        normalized = self._normalize_background_color(color_value)
        self._grid_container.set_preview_background(normalized)
        self.setProperty("preview_background_color", normalized)

    def update_preview(
        self,
        *,
        icon_size: int,
        frame_enabled: bool,
        frame_thickness: int,
        frame_color: str,
        highlight_color: str,
        grid_spacing_x: int = 0,
        grid_spacing_y: int = 0,
        preview_background_color: str = constants.DEFAULT_ICON_PREVIEW_BACKGROUND_COLOR,
    ) -> None:
        spacing_x = max(0, int(grid_spacing_x))
        spacing_y = max(0, int(grid_spacing_y))
        self._grid_layout.setHorizontalSpacing(spacing_x)
        self._grid_layout.setVerticalSpacing(spacing_y)
        self._grid_container.set_preview_spacing(spacing_x, spacing_y)
        self.setProperty("preview_grid_spacing_x", spacing_x)
        self.setProperty("preview_grid_spacing_y", spacing_y)
        normalized_bg = self._normalize_background_color(preview_background_color)
        self._apply_background_style(normalized_bg)
        for tile in self._tiles:
            tile.apply_style(
                icon_size=icon_size,
                frame_enabled=frame_enabled,
                frame_thickness=frame_thickness,
                frame_color=frame_color,
                highlight_color=highlight_color,
            )
