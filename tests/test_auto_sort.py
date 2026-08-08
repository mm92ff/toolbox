from __future__ import annotations

from unittest.mock import MagicMock

from app import constants
from app.domain.models import ToolboxEntry
from app.features.entries.controller_crud import (
    sort_entries_alphabetically,
    sort_entries_by_type,
)


def _section(entry_id: str, title: str, y: int) -> ToolboxEntry:
    return ToolboxEntry(
        entry_id=entry_id,
        title=title,
        kind=constants.ENTRY_KIND_SECTION,
        y=y,
        x=10,
    )


def _tool(entry_id: str, title: str, x: int, y: int, path: str = "/missing") -> ToolboxEntry:
    return ToolboxEntry(entry_id=entry_id, title=title, path=path, x=x, y=y)


def _titles_by_position(entries: list[ToolboxEntry], minimum_y: int, maximum_y: int) -> list[str]:
    tools = [
        entry
        for entry in entries
        if entry.is_tool and minimum_y < entry.y < maximum_y
    ]
    return [entry.custom_title or entry.title for entry in sorted(tools, key=lambda e: (e.y, e.x))]


def test_sort_entries_alphabetically_sorts_each_section_by_real_positions() -> None:
    owner = MagicMock()
    owner.current_auto_compact_left.return_value = True
    entries = [
        _section("section_1", "A Section", 100),
        _tool("z_tool", "Zeta", 10, 200),
        _tool("g_tool", "Gamma", 200, 200),
        _tool("a_tool", "Alpha", 10, 300),
        _section("section_2", "B Section", 500),
        _tool("o_tool", "Omega", 10, 600),
        _tool("b_tool", "Beta", 200, 600),
    ]
    ctx = MagicMock(entries=entries)

    sort_entries_alphabetically(owner, ctx)

    assert _titles_by_position(entries, 100, 500) == ["Alpha", "Gamma", "Zeta"]
    assert _titles_by_position(entries, 500, 10_000) == ["Beta", "Omega"]
    ctx.canvas.compact_tools.assert_not_called()
    owner.persist_toolbox_state.assert_called_once()
    owner.refresh_canvas.assert_called_once_with(ctx)


def test_sort_entries_alphabetically_uses_custom_title_and_preserves_other_section() -> None:
    owner = MagicMock()
    owner.current_auto_compact_left.return_value = True
    section1 = _section("section_1", "A Section", 100)
    section2 = _section("section_2", "B Section", 500)
    renamed = _tool("z_tool", "Zeta", 10, 200)
    renamed.custom_title = "Aardvark"
    section2_first = _tool("o_tool", "Omega", 10, 600)
    section2_second = _tool("b_tool", "Beta", 200, 600)
    entries = [
        section1,
        renamed,
        _tool("g_tool", "Gamma", 200, 200),
        section2,
        section2_first,
        section2_second,
    ]
    ctx = MagicMock(entries=entries)
    untouched = [(section2_first.x, section2_first.y), (section2_second.x, section2_second.y)]

    sort_entries_alphabetically(owner, ctx, section_entry=section1)

    assert _titles_by_position(entries, 100, 500) == ["Aardvark", "Gamma"]
    assert [(section2_first.x, section2_first.y), (section2_second.x, section2_second.y)] == untouched


def test_sort_entries_by_type_orders_folders_extensions_and_names(tmp_path) -> None:
    owner = MagicMock()
    owner.current_auto_compact_left.return_value = True
    folder = tmp_path / "folder"
    folder.mkdir()
    text_z = tmp_path / "z.txt"
    text_z.write_text("z", encoding="utf-8")
    text_a = tmp_path / "a.txt"
    text_a.write_text("a", encoding="utf-8")
    image = tmp_path / "pic.png"
    image.write_bytes(b"png")
    entries = [
        _tool("txt-z", "Zeta", 0, 0, str(text_z)),
        _tool("folder", "Folder", 100, 0, str(folder)),
        _tool("txt-a", "Alpha", 200, 0, str(text_a)),
        _tool("png", "Picture", 300, 0, str(image)),
        _tool("url", "Website", 400, 0, "https://example.invalid"),
    ]
    ctx = MagicMock(entries=entries)

    sort_entries_by_type(owner, ctx)

    assert [entry.title for entry in sorted(entries, key=lambda e: (e.y, e.x))] == [
        "Folder",
        "Picture",
        "Alpha",
        "Zeta",
        "Website",
    ]


def test_sort_entries_alphabetically_disabled_when_compact_off() -> None:
    owner = MagicMock()
    owner.current_auto_compact_left.return_value = False
    ctx = MagicMock(entries=[])

    sort_entries_alphabetically(owner, ctx)

    owner.persist_toolbox_state.assert_not_called()
    owner.status.showMessage.assert_called_with(
        "Auto-sort requires 'Auto-compact left' to be enabled.", 3500
    )
