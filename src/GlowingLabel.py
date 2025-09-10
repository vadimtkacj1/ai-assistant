from PyQt6.QtWidgets import (QLabel)
from PyQt6.QtCore import (Qt, QPropertyAnimation, QEasingCurve, pyqtProperty)
from PyQt6.QtGui import (QPainter, QColor, QPen)

class GlowingLabel(QLabel):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._glow_radius = 0
        self._glow_color = QColor(52, 152, 219)
        
        self.glow_animation = QPropertyAnimation(self, b"glow_radius")
        self.glow_animation.setDuration(1500)
        self.glow_animation.setLoopCount(-1)
        self.glow_animation.setStartValue(0)
        self.glow_animation.setEndValue(10)
        self.glow_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        
        # Set background to be transparent
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background-color: transparent; color: white;")

    def setGlowColor(self, color):
        self._glow_color = color
        self.update()

    def getGlowRadius(self):
        return self._glow_radius

    def setGlowRadius(self, radius):
        self._glow_radius = radius
        self.update()

    glow_radius = pyqtProperty(float, getGlowRadius, setGlowRadius)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw glow effect
        if self._glow_radius > 0:
            glow = self._glow_color
            for i in range(int(self._glow_radius)):
                alpha = int(127 * (1 - i / self._glow_radius))
                glow.setAlpha(alpha)
                painter.setPen(QPen(glow, i, Qt.PenStyle.SolidLine))
                painter.drawRoundedRect(self.rect().adjusted(i, i, -i, -i), 10, 10)

        # Draw the text
        painter.setPen(QPen(Qt.GlobalColor.white))
        painter.drawText(self.rect(), self.alignment(), self.text())
