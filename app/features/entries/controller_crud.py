#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CRUD and path handling helpers for entry controller."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtWidgets

from app import constants
from app.domain.models import ToolboxEntry
from app.domain.tab_context import ToolboxTabContext
from app.services.paths import resolve_supported_tool_path
from app.services.system_utils import display_name_from_path, normalize_tool_path
from app.ui.dialogs.tile_properties_dialog import TilePropertiesDialog

logger = logging.getLogger(__name__)


def path_log_label(raw_path: str) -> str:
    path = Path(raw_path).expanduser()
    label = path.name.strip()
    return label or str(path)


def extract_supported_paths(mime_data: QtCore.QMimeData) -> list[str]:
    supported: list[str] = []
    for url in mime_data.urls():
        local_path = url.toLocalFile()
        if not local_path:
            continue
        resolved = resolve_supported_tool_path(local_path)
        if resolved is not None:
            supported.append(str(resolved))
    return supported


def add_tools_from_dialog(owner: object, ctx: Optional[ToolboxTabContext] = None) -> None:
    ctx = ctx or owner.current_toolbox_context()
    if ctx is None:
        return
    files, _ = QtWidgets.QFileDialog.getOpenFileNames(
        owner, "Add Apps", str(Path.home()), constants.TOOL_FILE_FILTER
    )
    if files:
        add_tool_paths(owner, ctx, files)


def add_tool_paths(owner: object, ctx: ToolboxTabContext, paths: list[str]) -> None:
    if getattr(ctx, "browse_stack", None):
        owner.status.showMessage("Cannot add entries while browsing a folder.", 3000)
        return
    known_paths = {normalize_tool_path(entry.path) for entry in ctx.entries if entry.is_tool}
    added = 0
    skipped_invalid = 0
    for raw_path in paths:
        resolved = resolve_supported_tool_path(raw_path)
        if resolved is None:
            skipped_invalid += 1
            logger.warning("Skipping unsupported or missing tool path: %s", path_log_label(raw_path))
            continue
        normalized = normalize_tool_path(str(resolved))
        if normalized in known_paths:
            continue
        x, y = ctx.canvas.find_next_free_tool_position(ctx.entries)
        ctx.entries.append(
            ToolboxEntry(
                title=display_name_from_path(str(resolved)),
                kind=constants.ENTRY_KIND_TOOL,
                path=str(resolved),
                x=x,
                y=y,
            )
        )
        known_paths.add(normalized)
        added += 1
    if added and skipped_invalid:
        owner.persist_toolbox_state()
        owner.refresh_canvas(ctx)
        owner.status.showMessage(f"{added} entry/entries added, {skipped_invalid} invalid skipped.", 3500)
    elif added:
        owner.persist_toolbox_state()
        owner.refresh_canvas(ctx)
        owner.status.showMessage(f"{added} entry/entries added.", 3000)
    elif skipped_invalid:
        owner.status.showMessage("No entries added (invalid paths).", 3000)
    else:
        owner.status.showMessage("No new entries added.", 3000)


def add_section(
    owner: object,
    ctx: Optional[ToolboxTabContext] = None,
    preferred_y: Optional[int] = None,
) -> None:
    ctx = ctx or owner.current_toolbox_context()
    if ctx is None:
        return
    title, accepted = QtWidgets.QInputDialog.getText(owner, "Add Section", "Header:")
    title = title.strip()
    if not accepted or not title:
        return
    if preferred_y is None:
        section_y = ctx.canvas.find_next_section_y(ctx.entries)
    else:
        section_y = ctx.canvas.snap_section_y(ctx.entries, preferred_y)
    ctx.entries.append(
        ToolboxEntry(
            title=title,
            kind=constants.ENTRY_KIND_SECTION,
            x=constants.CANVAS_PADDING,
            y=section_y,
        )
    )
    owner.persist_toolbox_state()
    owner.refresh_canvas(ctx)
    owner.status.showMessage("Section added.", 3000)


def remove_selected(owner: object, ctx: Optional[ToolboxTabContext] = None) -> None:
    ctx = ctx or owner.current_toolbox_context()
    if ctx is None or not ctx.selected_ids:
        return
    count = len(ctx.selected_ids)
    removed_tools = any(entry.entry_id in ctx.selected_ids and entry.is_tool for entry in ctx.entries)
    ctx.entries = [entry for entry in ctx.entries if entry.entry_id not in ctx.selected_ids]
    ctx.selected_ids.clear()
    if removed_tools and owner.current_auto_compact_left():
        ctx.canvas.compact_tools(ctx.entries)
    owner.persist_toolbox_state()
    owner.refresh_canvas(ctx)
    owner.status.showMessage(f"{count} entry/entries removed.", 3000)


def rename_entry(owner: object, ctx: ToolboxTabContext, entry: ToolboxEntry) -> None:
    title, accepted = QtWidgets.QInputDialog.getText(owner, "Rename Entry", "Name:", text=entry.title)
    title = title.strip()
    if not accepted or not title:
        return
    entry.title = title
    owner.persist_toolbox_state()
    owner.refresh_canvas(ctx)


def edit_properties(owner: object, ctx: ToolboxTabContext, entry: ToolboxEntry) -> None:
    dialog = TilePropertiesDialog(entry, parent=owner)
    if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
        entry.custom_title = dialog.custom_title
        entry.custom_icon_path = dialog.custom_icon_path
        owner.persist_toolbox_state()
        owner.refresh_canvas(ctx)


def _display_title(entry: ToolboxEntry) -> str:
    return (entry.custom_title.strip() or entry.title).casefold()


def _tools_by_section(
    entries: list[ToolboxEntry],
) -> dict[str | None, list[ToolboxEntry]]:
    sections = sorted(
        (entry for entry in entries if entry.is_section),
        key=lambda entry: (entry.y, entry.x),
    )
    grouped: dict[str | None, list[ToolboxEntry]] = {}
    for tool in (entry for entry in entries if entry.is_tool):
        section_id: str | None = None
        for section in reversed(sections):
            if tool.y > section.y:
                section_id = section.entry_id
                break
        grouped.setdefault(section_id, []).append(tool)
    return grouped


def _assign_sorted_tools(
    tools: list[ToolboxEntry],
    *,
    key: object,
) -> None:
    positions = sorted(((tool.y, tool.x) for tool in tools))
    ordered = sorted(tools, key=key)  # type: ignore[arg-type]
    for tool, (y, x) in zip(ordered, positions, strict=True):
        tool.x = x
        tool.y = y


def _sort_selected_groups(
    owner: object,
    ctx: ToolboxTabContext,
    section_entry: ToolboxEntry | None,
    key: object,
    success_message: str,
) -> None:
    if not owner.current_auto_compact_left():
        owner.status.showMessage(
            "Auto-sort requires 'Auto-compact left' to be enabled.", 3500
        )
        return

    requested_section_id = section_entry.entry_id if section_entry is not None else None
    for section_id, tools in _tools_by_section(ctx.entries).items():
        if section_entry is not None and section_id != requested_section_id:
            continue
        _assign_sorted_tools(tools, key=key)

    owner.persist_toolbox_state()
    owner.refresh_canvas(ctx)
    owner.status.showMessage(success_message, 3000)


def sort_entries_alphabetically(
    owner: object,
    ctx: ToolboxTabContext,
    section_entry: ToolboxEntry | None = None,
) -> None:
    """Sort visible position slots by display title, without moving other sections."""

    _sort_selected_groups(
        owner,
        ctx,
        section_entry,
        _display_title,
        "Alphabetically sorted tools.",
    )


def _tool_type_key(entry: ToolboxEntry) -> tuple[int, str, str]:
    if not entry.path or entry.path.lower().startswith(("http://", "https://")):
        return (2, "", _display_title(entry))
    path = Path(entry.path)
    try:
        if path.is_dir():
            return (0, "", _display_title(entry))
        if path.is_file():
            return (1, path.suffix.casefold(), _display_title(entry))
    except OSError:
        pass
    return (2, "", _display_title(entry))


def sort_entries_by_type(
    owner: object,
    ctx: ToolboxTabContext,
    section_entry: ToolboxEntry | None = None,
) -> None:
    """Sort folders first, files by extension, and every group alphabetically."""

    _sort_selected_groups(
        owner,
        ctx,
        section_entry,
        _tool_type_key,
        "Tools sorted by type.",
    )
