import sys
from PySide6 import QtCore, QtGui, QtWidgets

class RoundedIconLabel(QtWidgets.QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._radius = 0

    def set_radius(self, radius: int):
        self._radius = max(0, radius)
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        pixmap = self.pixmap()
        if not pixmap or pixmap.isNull():
            super().paintEvent(event)
            return

        # Try to draw the base QLabel first to keep CSS background
        # BUT we don't want the QLabel to draw the pixmap because it draws it as a square!
        # Actually, QLabel draws both background and pixmap in its paintEvent.
        # If we want to keep the CSS background, we should use QStylePainter or paint the background.
        
        # Let's just create an image with rounded corners manually.
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        
        x = (self.width() - pixmap.width()) // 2
        y = (self.height() - pixmap.height()) // 2
        
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(x, y, pixmap.width(), pixmap.height()), self._radius, self._radius)
        
        painter.setClipPath(path)
        painter.drawPixmap(x, y, pixmap)

app = QtWidgets.QApplication(sys.argv)
w = QtWidgets.QWidget()
layout = QtWidgets.QVBoxLayout(w)

label = RoundedIconLabel()
label.set_radius(20)

# Create a black pixmap
pix = QtGui.QPixmap(100, 100)
pix.fill(QtGui.QColor("black"))
label.setPixmap(pix)

layout.addWidget(label)
w.setStyleSheet("background: white;")
w.show()

# We can save it to an image to verify
img = QtGui.QPixmap(w.size())
w.render(img)
img.save("test_out.png")
print("Saved test_out.png")
