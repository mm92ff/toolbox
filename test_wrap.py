import sys
from PySide6 import QtWidgets, QtGui, QtCore

app = QtWidgets.QApplication(sys.argv)

text = "SonnenzeitRechner-0.1.AppImage-x86_64"

class ElidedLabel(QtWidgets.QLabel):
    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        metrics = self.fontMetrics()
        rect = self.rect()
        
        option = QtGui.QTextOption()
        option.setWrapMode(QtGui.QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        option.setAlignment(self.alignment())
        
        layout = QtGui.QTextLayout(self.text(), self.font())
        layout.setTextOption(option)
        layout.beginLayout()
        
        y = 0
        line_count = 0
        max_lines = 2
        
        while True:
            line = layout.createLine()
            if not line.isValid():
                break
                
            line.setLineWidth(rect.width())
            
            if line_count == max_lines - 1:
                # Elide the rest
                remaining_text = self.text()[line.textStart():]
                elided_string = metrics.elidedText(remaining_text, QtCore.Qt.TextElideMode.ElideRight, rect.width())
                painter.drawText(QtCore.QRect(0, y, rect.width(), metrics.lineSpacing()), int(self.alignment()), elided_string)
                break
            else:
                line.draw(painter, QtCore.QPointF(0, y))
                
            y += metrics.lineSpacing()
            line_count += 1
            
        layout.endLayout()

label = ElidedLabel(text)
label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
label.resize(100, 50)
label.show()

# Run it headless just to see if it parses
QtCore.QTimer.singleShot(500, app.quit)
app.exec()
print("Success")
