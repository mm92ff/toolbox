from unittest.mock import MagicMock

import pytest
from PySide6 import QtWidgets

from app.domain.models import ToolboxEntry
from app.domain.tab_context import ToolboxTabContext
from app.features.entries.controller_crud import sort_entries_alphabetically
from app import constants


def test_sort_entries_alphabetically_full_tab():
    owner = MagicMock()
    owner.current_auto_compact_left.return_value = True
    
    entries = [
        ToolboxEntry(entry_id="section_1", title="A Section", kind=constants.ENTRY_KIND_SECTION, y=100, x=10),
        ToolboxEntry(entry_id="z_tool", title="Zeta", kind=constants.ENTRY_KIND_TOOL, y=200, x=10),
        ToolboxEntry(entry_id="g_tool", title="Gamma", kind=constants.ENTRY_KIND_TOOL, y=200, x=200),
        ToolboxEntry(entry_id="a_tool", title="Alpha", kind=constants.ENTRY_KIND_TOOL, y=300, x=10),
        
        ToolboxEntry(entry_id="section_2", title="B Section", kind=constants.ENTRY_KIND_SECTION, y=500, x=10),
        ToolboxEntry(entry_id="o_tool", title="Omega", kind=constants.ENTRY_KIND_TOOL, y=600, x=10),
        ToolboxEntry(entry_id="b_tool", title="Beta", kind=constants.ENTRY_KIND_TOOL, y=600, x=200),
    ]
    
    ctx = MagicMock()
    ctx.entries = entries
    
    # Need to simulate the canvas compaction
    def mock_compact_tools(ent):
        pass # In our mock we just want to verify the parameters were correctly prepared for compaction
        
    ctx.canvas.compact_tools.side_effect = mock_compact_tools
    
    sort_entries_alphabetically(owner, ctx, section_entry=None)
    
    # Verify that the y and x were temporarily set properly for compaction
    # Section 1 tools should have y = 101, x = 0
    # Section 2 tools should have y = 501, x = 0
    for e in entries:
        if e.is_tool:
            assert e.x == 0
            if e.title in ["Zeta", "Gamma", "Alpha"]:
                assert e.y == 101
            elif e.title in ["Omega", "Beta"]:
                assert e.y == 501
                
    owner.persist_toolbox_state.assert_called_once()
    owner.refresh_canvas.assert_called_once_with(ctx)
    ctx.canvas.compact_tools.assert_called_once_with(entries)


def test_sort_entries_alphabetically_single_section():
    owner = MagicMock()
    owner.current_auto_compact_left.return_value = True
    
    section1 = ToolboxEntry(entry_id="section_1", title="A Section", kind=constants.ENTRY_KIND_SECTION, y=100, x=10)
    section2 = ToolboxEntry(entry_id="section_2", title="B Section", kind=constants.ENTRY_KIND_SECTION, y=500, x=10)
    
    entries = [
        section1,
        ToolboxEntry(entry_id="z_tool", title="Zeta", kind=constants.ENTRY_KIND_TOOL, y=200, x=10),
        ToolboxEntry(entry_id="g_tool", title="Gamma", kind=constants.ENTRY_KIND_TOOL, y=200, x=200),
        
        section2,
        ToolboxEntry(entry_id="o_tool", title="Omega", kind=constants.ENTRY_KIND_TOOL, y=600, x=10),
        ToolboxEntry(entry_id="b_tool", title="Beta", kind=constants.ENTRY_KIND_TOOL, y=600, x=200),
    ]
    
    ctx = MagicMock()
    ctx.entries = entries
    
    sort_entries_alphabetically(owner, ctx, section_entry=section1)
    
    # Only section 1 tools should be modified
    z_tool = next(e for e in entries if e.title == "Zeta")
    g_tool = next(e for e in entries if e.title == "Gamma")
    o_tool = next(e for e in entries if e.title == "Omega")
    b_tool = next(e for e in entries if e.title == "Beta")
    
    assert z_tool.x == 0
    assert z_tool.y == 101
    assert g_tool.x == 0
    assert g_tool.y == 101
    
    # Section 2 tools should be untouched
    assert o_tool.x == 10
    assert o_tool.y == 600
    assert b_tool.x == 200
    assert b_tool.y == 600
    
    owner.persist_toolbox_state.assert_called_once()
    ctx.canvas.compact_tools.assert_called_once_with(entries)

def test_sort_entries_alphabetically_disabled_when_compact_off():
    owner = MagicMock()
    owner.current_auto_compact_left.return_value = False
    
    ctx = MagicMock()
    ctx.entries = []
    
    sort_entries_alphabetically(owner, ctx, section_entry=None)
    
    # Canvas should not be compacted if auto-compact is off
    owner.persist_toolbox_state.assert_not_called()
    owner.status.showMessage.assert_called_with("Auto-sort requires 'Auto-compact left' to be enabled.", 3500)
