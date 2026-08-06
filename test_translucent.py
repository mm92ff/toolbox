import sys
from PySide6 import QtCore, QtGui, QtWidgets

app = QtWidgets.QApplication(sys.argv)

popup = QtWidgets.QLabel(None)
popup.setObjectName("toolbox_hover_preview_popup")
popup.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
popup.setWindowFlags(
    QtCore.Qt.WindowType.ToolTip
    | QtCore.Qt.WindowType.FramelessWindowHint
    | QtCore.Qt.WindowType.WindowStaysOnTopHint
)
popup.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
popup.setStyleSheet("""
    QLabel#toolbox_hover_preview_popup {
        background: rgba(14, 18, 26, 228);
        border: 1px solid rgba(170, 188, 220, 160);
        border-radius: 8px;
        padding: 6px;
    }
""")

pix = QtGui.QPixmap(100, 100)
pix.fill(QtGui.QColor("red"))
popup.setPixmap(pix)

popup.show()

# render to image
img = QtGui.QPixmap(popup.size())
img.fill(QtCore.Qt.GlobalColor.transparent)
popup.render(img)
img.save("test_translucent.png")
print("Saved test_translucent.png")
