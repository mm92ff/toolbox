#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Canvas surface pointer interaction and box-selection events."""

from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets


class CanvasSurfaceInteractionMixin:
    def _entry_ids_in_selection_rect(self, selection_rect: QtCore.QRect) -> list[str]:
        normalized = selection_rect.normalized()
        selected_ids: list[str] = []
        for entry_id, widget in self._widgets.items():
            if not widget.isVisible():
                continue
            if normalized.intersects(widget.geometry()):
                selected_ids.append(entry_id)
        return selected_ids

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        pos = event.position().toPoint()
        if event.button() == QtCore.Qt.MouseButton.LeftButton and self.childAt(pos) is None:
            self._selection_active = True
            self._selection_additive = bool(
                QtWidgets.QApplication.keyboardModifiers()
                & QtCore.Qt.KeyboardModifier.ShiftModifier
            )
            self._selection_dragged = False
            self._selection_origin = pos
            self._selection_band.setGeometry(QtCore.QRect(pos, QtCore.QSize()))
            self._selection_band.show()
            event.accept()
            return
        if self.childAt(pos) is None:
            self.background_clicked.emit()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._selection_active and (event.buttons() & QtCore.Qt.MouseButton.LeftButton):
            current = event.position().toPoint()
            selection_rect = QtCore.QRect(self._selection_origin, current).normalized()
            self._selection_band.setGeometry(selection_rect)
            if selection_rect.width() >= 4 or selection_rect.height() >= 4:
                self._selection_dragged = True
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._selection_active and event.button() == QtCore.Qt.MouseButton.LeftButton:
            self._selection_active = False
            final_rect = self._selection_band.geometry()
            self._selection_band.hide()
            if self._selection_dragged:
                selected_ids = self._entry_ids_in_selection_rect(final_rect)
                self.area_selection_finished.emit(selected_ids, self._selection_additive)
            else:
                self.background_clicked.emit()
            self._selection_dragged = False
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event: QtGui.QContextMenuEvent) -> None:
        local_pos = event.pos()
        if self.childAt(local_pos) is None:
            self.background_context_requested.emit(local_pos, event.globalPos())
            event.accept()
            return
        super().contextMenuEvent(event)
