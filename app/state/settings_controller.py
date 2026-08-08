"""Central writer and revision broadcaster for application-wide settings."""

from __future__ import annotations

import copy
from logging import getLogger

from PySide6 import QtCore

from app.features.settings.io_snapshot import save_settings


class SharedSettingsController(QtCore.QObject):
    settings_changed = QtCore.Signal(str, int, object)

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self.revision = 0
        self._snapshot: dict[str, object] = {}
        self._logger = getLogger(__name__)

    def save_from(self, owner: object) -> None:
        """Persist through one coordinator, then notify the other views."""

        save_settings(owner, self._logger)
        full_snapshot = copy.deepcopy(owner._build_ui_settings_snapshot())
        # Geometry, active tab and splitter positions are window-local view state.
        full_snapshot.pop("window", None)
        full_snapshot.pop("toolbox_splitter_sizes", None)
        tabs = full_snapshot.get("tabs")
        if isinstance(tabs, dict):
            tabs.pop("current_index", None)
        snapshot = full_snapshot
        if snapshot == self._snapshot:
            return
        self._snapshot = snapshot
        self.revision += 1
        self.settings_changed.emit(
            str(getattr(owner, "window_id", "")), self.revision, snapshot
        )

    def snapshot(self) -> dict[str, object]:
        return copy.deepcopy(self._snapshot)

    def import_from(self, owner: object, snapshot: dict[str, object]) -> None:
        """Apply profile settings through the central writer and broadcaster."""

        owner._apply_imported_ui_settings(snapshot)
        owner._load_settings()
        self.save_from(owner)
