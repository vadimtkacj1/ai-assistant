from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import Qt, QPropertyAnimation

class AnimatedButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setMinimumHeight(40)
        self._animation = QPropertyAnimation(self, b"geometry")
        self._animation.setDuration(100)
        self._base_stylesheet = ""
        self._hover_stylesheet = ""
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def enterEvent(self, event):
        self._animation.setEndValue(self.geometry().adjusted(-2, -2, 2, 2))
        self._animation.start()
        if self._hover_stylesheet:
            self.setStyleSheet(self._hover_stylesheet)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._animation.setEndValue(self.geometry().adjusted(2, 2, -2, -2))
        self._animation.start()
        if self._base_stylesheet:
            self.setStyleSheet(self._base_stylesheet)
        super().leaveEvent(event)

    def setStyleSheets(self, base, hover):
        self._base_stylesheet = base
        self._hover_stylesheet = hover
        self.setStyleSheet(base)