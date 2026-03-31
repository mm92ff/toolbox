#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Diagnostics helpers for toolbox entries."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

from app.domain.models import ToolboxTabData
from app.services.paths import resolve_supported_tool_path


@dataclass(frozen=True)
class BrokenToolEntry:
    """Represents one invalid tool entry inside a toolbox tab."""

    tab_id: str
    tab_title: str
    entry_id: str
    entry_title: str
    path: str
    reason: str


def _expanded_candidate_path(raw_path: str) -> str:
    return os.path.expandvars((raw_path or "").strip())


def _is_tool_path_valid(raw_path: str) -> bool:
    normalized = _expanded_candidate_path(raw_path)
    if not normalized:
        return False
    return resolve_supported_tool_path(normalized) is not None


def find_broken_tool_entries(tabs: Iterable[ToolboxTabData]) -> list[BrokenToolEntry]:
    """Return all tool entries that currently point to missing/invalid paths."""

    broken: list[BrokenToolEntry] = []
    for tab in tabs:
        for entry in tab.entries:
            if not entry.is_tool:
                continue

            entry_path = _expanded_candidate_path(entry.path)
            if not entry_path:
                broken.append(
                    BrokenToolEntry(
                        tab_id=tab.tab_id,
                        tab_title=tab.title,
                        entry_id=entry.entry_id,
                        entry_title=entry.title,
                        path=entry.path,
                        reason="Empty path",
                    )
                )
                continue

            if not _is_tool_path_valid(entry_path):
                broken.append(
                    BrokenToolEntry(
                        tab_id=tab.tab_id,
                        tab_title=tab.title,
                        entry_id=entry.entry_id,
                        entry_title=entry.title,
                        path=entry.path,
                        reason="Path not found or unreachable",
                    )
                )

    broken.sort(key=lambda item: (item.tab_title.lower(), item.entry_title.lower(), item.entry_id))
    return broken
