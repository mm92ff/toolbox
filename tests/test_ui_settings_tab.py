from PySide6 import QtWidgets

from app.ui.tabs.settings_tab import create_settings_tab
from app import constants

def test_settings_tab_has_subtabs():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    tab, _widgets = create_settings_tab()
    
    # Root layout must be a QVBoxLayout
    assert isinstance(tab.layout(), QtWidgets.QVBoxLayout)
    
    # We expect a QTabWidget inside
    tab_widget = None
    for i in range(tab.layout().count()):
        item = tab.layout().itemAt(i).widget()
        if isinstance(item, QtWidgets.QTabWidget):
            tab_widget = item
            break
            
    assert tab_widget is not None, "Settings tab is missing the QTabWidget for subtabs"
    
    # Check that there are at least 3 tabs
    assert tab_widget.count() >= 3
    
    # Verify the tab names
    tab_texts = [tab_widget.tabText(i) for i in range(tab_widget.count())]
    assert "Appearance & Layout" in tab_texts
    assert "Sections & Colors" in tab_texts
    assert "System" in tab_texts
    assert constants.WIDGET_RESPONSIVE_TOOLBOX_LAYOUT_CHECKBOX in _widgets
    assert _widgets[
        constants.WIDGET_RESPONSIVE_TOOLBOX_LAYOUT_CHECKBOX
    ].isChecked()
