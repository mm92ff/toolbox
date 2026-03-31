#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Persistence helpers for toolbox tabs and entries."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Iterable

from app import constants
from app.domain.models import ToolboxEntry, ToolboxTabData
from app.services.json_io import read_json_utf8, write_json_utf8_atomic

logger = logging.getLogger(__name__)


def get_tools_file_path(config_dir: Path) -> Path:
    """Return the JSON file path used for persisted toolbox tabs."""
    return config_dir / constants.TOOL_CONFIG_FILENAME


def load_toolbox_tabs(config_dir: Path) -> list[ToolboxTabData]:
    """Load toolbox tabs from disk, including backward-compatible legacy formats."""
    tools_file = get_tools_file_path(config_dir)
    if not tools_file.exists():
        return []

    try:
        payload = read_json_utf8(tools_file)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not load toolbox config '%s': %s", tools_file.name, exc)
        return []

    if isinstance(payload, dict) and isinstance(payload.get("tabs"), list):
        tabs: list[ToolboxTabData] = []
        for raw_tab in payload["tabs"]:
            if not isinstance(raw_tab, dict):
                continue
            try:
                tabs.append(ToolboxTabData.from_dict(raw_tab))
            except (TypeError, ValueError) as exc:
                logger.warning("Skipping invalid toolbox tab: %s", exc)
        return tabs

    if isinstance(payload, dict):
        raw_entries = payload.get("entries") or payload.get("tools") or []
    elif isinstance(payload, list):
        raw_entries = payload
    else:
        logger.warning(
            "Unexpected toolbox state root type in '%s': %s",
            tools_file.name,
            type(payload).__name__,
        )
        return []

    if not isinstance(raw_entries, list):
        logger.warning("Unexpected toolbox entries format in '%s'", tools_file.name)
        return []

    entries: list[ToolboxEntry] = []
    for raw_entry in raw_entries:
        if not isinstance(raw_entry, dict):
            continue
        try:
            entries.append(ToolboxEntry.from_dict(raw_entry))
        except (TypeError, ValueError) as exc:
            logger.warning("Skipping invalid toolbox entry: %s", exc)

    return [ToolboxTabData(title=constants.DEFAULT_TOOLBOX_TAB_TITLE, entries=entries)]


def save_toolbox_tabs(config_dir: Path, tabs: Iterable[ToolboxTabData]) -> None:
    """Persist toolbox tabs atomically as UTF-8 encoded JSON."""
    tools_file = get_tools_file_path(config_dir)
    payload = {
        "version": 3,
        "tabs": [tab.to_dict() for tab in tabs],
    }
    write_json_utf8_atomic(tools_file, payload, ensure_ascii=False, indent=2)
