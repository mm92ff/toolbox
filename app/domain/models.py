#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Structured data models for the toolbox launcher."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Literal, NotRequired, TypedDict, cast

from app import constants

LaunchWindowStyle = Literal["normal", "minimized", "maximized", "hidden"]


class ToolboxEntryDict(TypedDict):
    id: str
    title: str
    kind: str
    path: str
    x: int
    y: int
    always_run_as_admin: bool
    launch_arguments: str
    launch_working_directory: str
    launch_wait: bool
    launch_window_style: LaunchWindowStyle
    section_line_color: NotRequired[str]
    section_title_color: NotRequired[str]


class ToolboxTabDict(TypedDict):
    id: str
    title: str
    entries: list[ToolboxEntryDict]
    is_primary: bool


def _as_str(value: object, default: str = "") -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return default
    return str(value)


def _as_int(value: object, default: int) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return default
        try:
            return int(text)
        except ValueError:
            return default
    return default


def _as_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def _normalize_launch_window_style(value: object) -> LaunchWindowStyle:
    style = _as_str(value, "normal").strip().lower() or "normal"
    if style in {"normal", "minimized", "maximized", "hidden"}:
        return cast(LaunchWindowStyle, style)
    return "normal"


@dataclass(slots=True)
class ToolboxEntry:
    """One movable entry on a toolbox canvas."""

    title: str
    kind: str = constants.ENTRY_KIND_TOOL
    path: str = ""
    x: int = constants.CANVAS_PADDING
    y: int = constants.CANVAS_PADDING
    always_run_as_admin: bool = False
    launch_arguments: str = ""
    launch_working_directory: str = ""
    launch_wait: bool = False
    launch_window_style: LaunchWindowStyle = "normal"
    section_line_color: str = ""
    section_title_color: str = ""
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    @property
    def is_tool(self) -> bool:
        return self.kind == constants.ENTRY_KIND_TOOL

    @property
    def is_section(self) -> bool:
        return self.kind == constants.ENTRY_KIND_SECTION

    def to_dict(self) -> ToolboxEntryDict:
        payload: ToolboxEntryDict = {
            "id": self.entry_id,
            "title": self.title,
            "kind": self.kind,
            "path": self.path,
            "x": self.x,
            "y": self.y,
            "always_run_as_admin": self.always_run_as_admin,
            "launch_arguments": self.launch_arguments,
            "launch_working_directory": self.launch_working_directory,
            "launch_wait": self.launch_wait,
            "launch_window_style": self.launch_window_style,
        }
        if self.is_section and self.section_line_color.strip():
            payload["section_line_color"] = self.section_line_color.strip()
        if self.is_section and self.section_title_color.strip():
            payload["section_title_color"] = self.section_title_color.strip()
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ToolboxEntry":
        title = _as_str(payload.get("title")).strip() or _as_str(payload.get("name")).strip()
        kind = _as_str(payload.get("kind"), constants.ENTRY_KIND_TOOL).strip()
        path = _as_str(payload.get("path")).strip()
        entry_id = (
            _as_str(payload.get("id")).strip()
            or _as_str(payload.get("entry_id")).strip()
            or uuid.uuid4().hex
        )
        if kind not in {constants.ENTRY_KIND_TOOL, constants.ENTRY_KIND_SECTION}:
            raise ValueError(f"Unsupported entry kind: {kind}")
        if not title:
            raise ValueError("Entry requires a non-empty title.")
        if kind == constants.ENTRY_KIND_TOOL and not path:
            raise ValueError("Tool entry requires a non-empty path.")
        launch_window_style = _normalize_launch_window_style(payload.get("launch_window_style"))
        return cls(
            title=title,
            kind=kind,
            path=path,
            x=_as_int(payload.get("x"), constants.CANVAS_PADDING),
            y=_as_int(payload.get("y"), constants.CANVAS_PADDING),
            always_run_as_admin=_as_bool(payload.get("always_run_as_admin"), False),
            launch_arguments=_as_str(payload.get("launch_arguments")).strip(),
            launch_working_directory=_as_str(payload.get("launch_working_directory")).strip(),
            launch_wait=_as_bool(payload.get("launch_wait"), False),
            launch_window_style=launch_window_style,
            section_line_color=_as_str(payload.get("section_line_color")).strip(),
            section_title_color=_as_str(payload.get("section_title_color")).strip(),
            entry_id=entry_id,
        )


@dataclass(slots=True)
class ToolboxTabData:
    """A single toolbox page with its own entries."""

    title: str
    entries: list[ToolboxEntry] = field(default_factory=list)
    tab_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    is_primary: bool = False

    def to_dict(self) -> ToolboxTabDict:
        return {
            "id": self.tab_id,
            "title": self.title,
            "entries": [entry.to_dict() for entry in self.entries],
            "is_primary": self.is_primary,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ToolboxTabData":
        title = (
            _as_str(payload.get("title"), constants.DEFAULT_TOOLBOX_TAB_TITLE).strip()
            or constants.DEFAULT_TOOLBOX_TAB_TITLE
        )
        tab_id = _as_str(payload.get("id")).strip() or uuid.uuid4().hex
        raw_entries = payload.get("entries")
        if not isinstance(raw_entries, list):
            raw_entries = payload.get("tools")
        if not isinstance(raw_entries, list):
            raw_entries = []
        is_primary = _as_bool(payload.get("is_primary"), False)
        entries: list[ToolboxEntry] = []
        for raw_entry in raw_entries:
            if not isinstance(raw_entry, dict):
                continue
            entries.append(ToolboxEntry.from_dict(cast(dict[str, object], raw_entry)))
        return cls(title=title, entries=entries, tab_id=tab_id, is_primary=is_primary)
