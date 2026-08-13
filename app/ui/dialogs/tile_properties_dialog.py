#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dialog for editing tile properties."""

from __future__ import annotations

from typing import Optional

from PySide6 import QtWidgets

from app.domain.models import ToolboxEntry


class TilePropertiesDialog(QtWidgets.QDialog):
    """Dialog to edit custom title and icon for a toolbox entry."""

    def __init__(self, entry: ToolboxEntry, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Eigenschaften bearbeiten")
        self.setMinimumWidth(400)
        self.entry = entry

        self.custom_title = entry.custom_title or entry.title
        self.custom_icon_path = entry.custom_icon_path or ""

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        form_layout = QtWidgets.QFormLayout()

        self.title_input = QtWidgets.QLineEdit(self.custom_title)
        form_layout.addRow("Anzeigename:", self.title_input)

        self.icon_layout = QtWidgets.QHBoxLayout()
        self.icon_input = QtWidgets.QLineEdit(self.custom_icon_path)
        self.icon_input.setPlaceholderText("Standard-Icon verwenden (leer lassen)")
        self.icon_browse_btn = QtWidgets.QPushButton("Durchsuchen...")
        self.icon_browse_btn.clicked.connect(self._browse_icon)

        self.icon_layout.addWidget(self.icon_input)
        self.icon_layout.addWidget(self.icon_browse_btn)

        form_layout.addRow("Benutzerdefiniertes Icon:", self.icon_layout)

        layout.addLayout(form_layout)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok
            | QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_icon(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Icon auswählen",
            "",
            "Bilder (*.png *.jpg *.jpeg *.svg *.ico);;Alle Dateien (*)",
        )
        if path:
            self.icon_input.setText(path)

    def accept(self) -> None:
        self.custom_title = self.title_input.text().strip()
        self.custom_icon_path = self.icon_input.text().strip()

        # If the user enters the original title, treat it as "no custom title" to avoid redundancy
        if self.custom_title == self.entry.title:
            self.custom_title = ""

        super().accept()
