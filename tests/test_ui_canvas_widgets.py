from PySide6 import QtCore, QtGui, QtWidgets

from app.domain.models import ToolboxEntry
from app.ui.widgets.canvas_widgets import ToolTileWidget

def test_tool_tile_widget_overlay_mode():
    _app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    entry = ToolboxEntry(entry_id="test", title="Test App", path="/tmp/test")
    # create a dummy icon
    pixmap = QtGui.QPixmap(64, 64)
    pixmap.fill(QtCore.Qt.GlobalColor.blue)
    icon = QtGui.QIcon(pixmap)

    # We need a parent widget, normally CanvasSurfaceWidget, but any QWidget is fine
    widget = ToolTileWidget(entry, icon, icon_size=64, parent=None)

    # By default, overlay is False
    assert widget._overlay_mode is False
    assert widget.title_label.parent() == widget

    # Enable overlay mode
    widget.set_overlay_mode(True)
    # In production, set_icon_size is called after overlay mode changes
    widget.set_icon_size(64)

    assert widget._overlay_mode is True
    # The title_label should now be reparented to icon_label
    assert widget.title_label.parent() == widget.icon_label


def test_tool_tile_widget_uses_manual_title_font_size():
    entry = ToolboxEntry(entry_id="font-test", title="Large Text", path="/tmp/test")
    icon = QtGui.QIcon(QtGui.QPixmap(64, 64))
    widget = ToolTileWidget(
        entry,
        icon,
        icon_size=64,
        tile_font_size=22,
    )

    assert widget.title_label.font().pixelSize() == 22
    assert widget.file_count_label.font().pixelSize() == 21
