#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for typed model parsing and serialization contracts."""

from __future__ import annotations

from app import constants
from app.domain.models import ToolboxEntry, ToolboxTabData


class TestToolboxEntryParsing:
    def test_from_dict_coerces_numeric_and_bool_fields(self) -> None:
        entry = ToolboxEntry.from_dict(
            {
                "title": "Demo",
                "kind": constants.ENTRY_KIND_TOOL,
                "path": r"C:\Tools\demo.exe",
                "x": "120",
                "y": "240",
                "always_run_as_admin": "true",
                "launch_wait": "1",
                "launch_window_style": "MAXIMIZED",
            }
        )

        assert entry.x == 120
        assert entry.y == 240
        assert entry.always_run_as_admin is True
        assert entry.launch_wait is True
        assert entry.launch_window_style == "maximized"

    def test_from_dict_uses_safe_defaults_for_invalid_values(self) -> None:
        entry = ToolboxEntry.from_dict(
            {
                "title": "Demo",
                "kind": constants.ENTRY_KIND_TOOL,
                "path": r"C:\Tools\demo.exe",
                "x": object(),
                "y": "",
                "launch_window_style": "unsupported-style",
            }
        )

        assert entry.x == constants.CANVAS_PADDING
        assert entry.y == constants.CANVAS_PADDING
        assert entry.launch_window_style == "normal"

    def test_from_dict_preserves_section_colors(self) -> None:
        entry = ToolboxEntry.from_dict(
            {
                "title": "Header",
                "kind": constants.ENTRY_KIND_SECTION,
                "x": 10,
                "y": 20,
                "section_line_color": "#123456",
                "section_title_color": "#abcdef",
            }
        )

        assert entry.section_line_color == "#123456"
        assert entry.section_title_color == "#abcdef"


class TestToolboxTabParsing:
    def test_from_dict_accepts_legacy_tools_key(self) -> None:
        tab = ToolboxTabData.from_dict(
            {
                "title": "Legacy",
                "tools": [
                    {
                        "title": "Demo",
                        "kind": constants.ENTRY_KIND_TOOL,
                        "path": r"C:\Tools\demo.exe",
                    }
                ],
                "is_primary": "yes",
            }
        )

        assert tab.title == "Legacy"
        assert len(tab.entries) == 1
        assert tab.is_primary is True

    def test_from_dict_ignores_non_list_entries_payload(self) -> None:
        tab = ToolboxTabData.from_dict(
            {
                "title": "Invalid Entries",
                "entries": {"not": "a-list"},
            }
        )

        assert tab.title == "Invalid Entries"
        assert tab.entries == []

    def test_from_dict_parses_tab_background_color(self) -> None:
        tab = ToolboxTabData.from_dict(
            {
                "title": "Colored",
                "entries": [],
                "background_color": "#223344",
            }
        )

        assert tab.background_color == "#223344"
