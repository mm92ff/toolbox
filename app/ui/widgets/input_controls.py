#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Small reusable input widgets with guarded wheel behavior."""

from __future__ import annotations

from PySide6 import QtGui, QtWidgets


class NoWheelComboBox(QtWidgets.QComboBox):
    """Combo box that ignores mouse-wheel value changes."""

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        event.ignore()


class NoWheelSpinBox(QtWidgets.QSpinBox):
    """Spin box that ignores mouse-wheel value changes."""

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:
        event.ignore()
