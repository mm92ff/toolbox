"""Canonical, widget-free toolbox state and persistence coordination."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from PySide6 import QtCore

from app import constants
from app.domain.models import ToolboxEntry, ToolboxTabData
from app.services.storage import load_toolbox_tabs, save_toolbox_tabs


class StaleToolboxStateError(RuntimeError):
    """Raised when a view attempts to commit against an older revision."""


@dataclass(frozen=True, slots=True)
class ToolboxStateChange:
    """Description of one committed change to the shared model."""

    revision: int
    origin_window_id: str
    kind: str
    affected_tab_ids: tuple[str, ...] = ()
    affected_entry_ids: tuple[str, ...] = ()
    structural_change: bool = False


class ToolboxStateRepository(QtCore.QObject):
    """Own the canonical tabs, global history, and the only tools.json writer."""

    state_changed = QtCore.Signal(object, object)
    persistence_failed = QtCore.Signal(str)

    def __init__(
        self,
        config_dir: Path,
        parent: QtCore.QObject | None = None,
        *,
        max_undo_steps: int = 50,
        debounce_ms: int = 120,
    ) -> None:
        super().__init__(parent)
        self.config_dir = Path(config_dir)
        self._max_undo_steps = max(1, int(max_undo_steps))
        self._revision = 0
        self._undo_stack: list[list[dict[str, object]]] = []
        self._redo_stack: list[list[dict[str, object]]] = []
        self._tabs = self._normalize_tabs(load_toolbox_tabs(self.config_dir))
        self._last_persisted = self._state_dicts()
        self._write_timer = QtCore.QTimer(self)
        self._write_timer.setSingleShot(True)
        self._write_timer.setInterval(max(0, int(debounce_ms)))
        self._write_timer.timeout.connect(self.flush)

    @property
    def revision(self) -> int:
        return self._revision

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    @staticmethod
    def _normalize_tabs(tabs: Iterable[ToolboxTabData]) -> list[ToolboxTabData]:
        normalized = [ToolboxTabData.from_dict(tab.to_dict()) for tab in tabs]
        if not normalized:
            normalized = [
                ToolboxTabData(
                    title=constants.DEFAULT_TOOLBOX_TAB_TITLE,
                    entries=[],
                    is_primary=True,
                )
            ]

        seen_tabs: set[str] = set()
        first_primary = next(
            (index for index, tab in enumerate(normalized) if tab.is_primary), 0
        )
        for index, tab in enumerate(normalized):
            if tab.tab_id in seen_tabs:
                raise ValueError(f"Duplicate tab id: {tab.tab_id}")
            seen_tabs.add(tab.tab_id)
            tab.is_primary = index == first_primary
            seen_entries: set[str] = set()
            for entry in tab.entries:
                if entry.entry_id in seen_entries:
                    raise ValueError(
                        f"Duplicate entry id in tab {tab.tab_id}: {entry.entry_id}"
                    )
                seen_entries.add(entry.entry_id)
        return normalized

    def _state_dicts(self) -> list[dict[str, object]]:
        return [copy.deepcopy(tab.to_dict()) for tab in self._tabs]

    def snapshot(self) -> list[ToolboxTabData]:
        """Return a defensive model snapshot."""

        return [ToolboxTabData.from_dict(tab) for tab in self._state_dicts()]

    def snapshot_dicts(self) -> list[dict[str, object]]:
        return self._state_dicts()

    def tab(self, tab_id: str) -> ToolboxTabData | None:
        return next((tab for tab in self.snapshot() if tab.tab_id == tab_id), None)

    def _require_tab(self, tabs: list[ToolboxTabData], tab_id: str) -> ToolboxTabData:
        tab = next((candidate for candidate in tabs if candidate.tab_id == tab_id), None)
        if tab is None:
            raise KeyError(f"Unknown tab id: {tab_id}")
        return tab

    def create_tab(
        self,
        title: str,
        *,
        origin_window_id: str = "",
        background_color: str = "",
    ) -> str:
        tabs = self.snapshot()
        created = ToolboxTabData(
            title=title.strip() or constants.DEFAULT_TOOLBOX_TAB_TITLE,
            background_color=background_color.strip(),
        )
        tabs.append(created)
        self.replace(
            tabs,
            origin_window_id=origin_window_id,
            kind="create-tab",
            affected_tab_ids=(created.tab_id,),
        )
        return created.tab_id

    def rename_tab(self, tab_id: str, title: str, *, origin_window_id: str = "") -> bool:
        tabs = self.snapshot()
        tab = self._require_tab(tabs, tab_id)
        normalized = title.strip() or constants.DEFAULT_TOOLBOX_TAB_TITLE
        if tab.title == normalized:
            return False
        tab.title = normalized
        return self.replace(
            tabs,
            origin_window_id=origin_window_id,
            kind="rename-tab",
            affected_tab_ids=(tab_id,),
        )

    def delete_tab(self, tab_id: str, *, origin_window_id: str = "") -> bool:
        tabs = self.snapshot()
        removed = self._require_tab(tabs, tab_id)
        if len(tabs) == 1:
            raise ValueError("The primary toolbox tab cannot be deleted")
        tabs.remove(removed)
        if removed.is_primary:
            tabs[0].is_primary = True
        return self.replace(
            tabs,
            origin_window_id=origin_window_id,
            kind="delete-tab",
            affected_tab_ids=(tab_id,),
        )

    def reorder_tabs(
        self, tab_ids: Iterable[str], *, origin_window_id: str = ""
    ) -> bool:
        requested = list(tab_ids)
        tabs = self.snapshot()
        known = {tab.tab_id: tab for tab in tabs}
        if len(requested) != len(known) or set(requested) != set(known):
            raise ValueError("Tab order must contain every known tab id exactly once")
        return self.replace(
            [known[tab_id] for tab_id in requested],
            origin_window_id=origin_window_id,
            kind="reorder-tabs",
            affected_tab_ids=requested,
        )

    def add_entries(
        self,
        tab_id: str,
        entries: Iterable[ToolboxEntry],
        *,
        origin_window_id: str = "",
    ) -> bool:
        tabs = self.snapshot()
        tab = self._require_tab(tabs, tab_id)
        additions = [ToolboxEntry.from_dict(entry.to_dict()) for entry in entries]
        if not additions:
            return False
        tab.entries.extend(additions)
        return self.replace(
            tabs,
            origin_window_id=origin_window_id,
            kind="add-entries",
            structural_change=False,
            affected_tab_ids=(tab_id,),
            affected_entry_ids=(entry.entry_id for entry in additions),
        )

    def update_entry(
        self,
        tab_id: str,
        entry_id: str,
        changes: dict[str, object],
        *,
        origin_window_id: str = "",
    ) -> bool:
        tabs = self.snapshot()
        tab = self._require_tab(tabs, tab_id)
        entry = next((item for item in tab.entries if item.entry_id == entry_id), None)
        if entry is None:
            raise KeyError(f"Unknown entry id: {entry_id}")
        payload = entry.to_dict()
        allowed = {
            "title",
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
        }
        for key, value in changes.items():
            if key not in allowed:
                raise ValueError(f"Unsupported entry field: {key}")
            payload[key] = value  # type: ignore[literal-required]
        replacement = ToolboxEntry.from_dict(payload)
        if replacement.to_dict() == entry.to_dict():
            return False
        tab.entries[tab.entries.index(entry)] = replacement
        return self.replace(
            tabs,
            origin_window_id=origin_window_id,
            kind="update-entry",
            structural_change=False,
            affected_tab_ids=(tab_id,),
            affected_entry_ids=(entry_id,),
        )

    def move_entries(
        self,
        tab_id: str,
        positions: dict[str, tuple[int, int]],
        *,
        origin_window_id: str = "",
    ) -> bool:
        tabs = self.snapshot()
        tab = self._require_tab(tabs, tab_id)
        known = {entry.entry_id: entry for entry in tab.entries}
        unknown = set(positions) - set(known)
        if unknown:
            raise KeyError(f"Unknown entry id: {sorted(unknown)[0]}")
        changed = False
        for entry_id, (x, y) in positions.items():
            entry = known[entry_id]
            if (entry.x, entry.y) != (int(x), int(y)):
                entry.x, entry.y = int(x), int(y)
                changed = True
        if not changed:
            return False
        return self.replace(
            tabs,
            origin_window_id=origin_window_id,
            kind="move-entries",
            structural_change=False,
            affected_tab_ids=(tab_id,),
            affected_entry_ids=positions,
        )

    def delete_entries(
        self,
        tab_id: str,
        entry_ids: Iterable[str],
        *,
        origin_window_id: str = "",
    ) -> bool:
        requested = set(entry_ids)
        tabs = self.snapshot()
        tab = self._require_tab(tabs, tab_id)
        known = {entry.entry_id for entry in tab.entries}
        unknown = requested - known
        if unknown:
            raise KeyError(f"Unknown entry id: {sorted(unknown)[0]}")
        if not requested:
            return False
        tab.entries = [entry for entry in tab.entries if entry.entry_id not in requested]
        return self.replace(
            tabs,
            origin_window_id=origin_window_id,
            kind="delete-entries",
            structural_change=False,
            affected_tab_ids=(tab_id,),
            affected_entry_ids=requested,
        )

    def set_tab_background(
        self, tab_id: str, color: str, *, origin_window_id: str = ""
    ) -> bool:
        tabs = self.snapshot()
        tab = self._require_tab(tabs, tab_id)
        normalized = color.strip()
        if tab.background_color == normalized:
            return False
        tab.background_color = normalized
        return self.replace(
            tabs,
            origin_window_id=origin_window_id,
            kind="set-tab-background",
            affected_tab_ids=(tab_id,),
        )

    def _push_history(self, state: list[dict[str, object]]) -> None:
        self._undo_stack.append(copy.deepcopy(state))
        if len(self._undo_stack) > self._max_undo_steps:
            del self._undo_stack[: -self._max_undo_steps]
        self._redo_stack.clear()

    def replace(
        self,
        state: Iterable[dict[str, object] | ToolboxTabData],
        *,
        origin_window_id: str = "",
        kind: str = "replace",
        structural_change: bool = True,
        affected_tab_ids: Iterable[str] = (),
        affected_entry_ids: Iterable[str] = (),
        expected_revision: int | None = None,
    ) -> bool:
        """Validate and commit a complete state produced by a view command."""

        if expected_revision is not None and expected_revision != self._revision:
            raise StaleToolboxStateError(
                f"Expected revision {expected_revision}, current revision is {self._revision}"
            )

        tabs: list[ToolboxTabData] = []
        for item in state:
            tabs.append(
                ToolboxTabData.from_dict(item.to_dict())
                if isinstance(item, ToolboxTabData)
                else ToolboxTabData.from_dict(item)
            )
        normalized = self._normalize_tabs(tabs)
        new_state = [tab.to_dict() for tab in normalized]
        old_state = self._state_dicts()
        if new_state == old_state:
            return False
        self._push_history(old_state)
        self._tabs = normalized
        self._revision += 1
        self._schedule_write()
        self._emit_change(
            origin_window_id,
            kind,
            structural_change,
            affected_tab_ids,
            affected_entry_ids,
        )
        return True

    def _schedule_write(self) -> None:
        if self._write_timer.interval() == 0:
            self.flush()
        else:
            self._write_timer.start()

    def _emit_change(
        self,
        origin: str,
        kind: str,
        structural: bool,
        tab_ids: Iterable[str] = (),
        entry_ids: Iterable[str] = (),
    ) -> None:
        change = ToolboxStateChange(
            revision=self._revision,
            origin_window_id=origin,
            kind=kind,
            affected_tab_ids=tuple(tab_ids),
            affected_entry_ids=tuple(entry_ids),
            structural_change=structural,
        )
        self.state_changed.emit(change, self.snapshot_dicts())

    def undo(self, origin_window_id: str = "") -> bool:
        if not self._undo_stack:
            return False
        current = self._state_dicts()
        previous = self._undo_stack.pop()
        self._redo_stack.append(current)
        self._tabs = self._normalize_tabs(
            ToolboxTabData.from_dict(item) for item in previous
        )
        self._revision += 1
        self._schedule_write()
        self._emit_change(origin_window_id, "undo", True)
        return True

    def redo(self, origin_window_id: str = "") -> bool:
        if not self._redo_stack:
            return False
        current = self._state_dicts()
        following = self._redo_stack.pop()
        self._undo_stack.append(current)
        self._tabs = self._normalize_tabs(
            ToolboxTabData.from_dict(item) for item in following
        )
        self._revision += 1
        self._schedule_write()
        self._emit_change(origin_window_id, "redo", True)
        return True

    def flush(self) -> bool:
        """Persist the latest revision immediately. Return whether a write occurred."""

        self._write_timer.stop()
        state = self._state_dicts()
        if state == self._last_persisted:
            return False
        try:
            save_toolbox_tabs(self.config_dir, self._tabs)
        except OSError as exc:
            self.persistence_failed.emit(str(exc))
            return False
        self._last_persisted = state
        return True

    def shutdown(self) -> None:
        self.flush()
