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

