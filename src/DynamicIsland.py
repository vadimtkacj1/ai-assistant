from PyQt6.QtWidgets import (QWidget)
from PyQt6.QtCore import (Qt, QPoint, QTimer)
from PyQt6.QtGui import (QPainter, QColor, QPainterPath, QLinearGradient, QPen)
import math

class DynamicIsland(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Fixed size - no more dynamic width changes
        self.setFixedSize(300, 60)
        self.status = "idle"
        self.wave_offset = 0
        self.wave_timer = QTimer()
        self.wave_timer.timeout.connect(self.update_wave)
        self.wave_timer.start(30)  # Update more frequently for smoother animation
        self.wave_points = []
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background-color: transparent;")
        
        # Pre-calculate wave points with higher density
        self.precalculate_wave_points()
        
    def precalculate_wave_points(self):
        self.wave_points = []
        # Increase density of points for smoother waves
        for x in range(0, self.width(), 2):
            self.wave_points.append(x)
            
    def update_wave(self):
        self.wave_offset += 0.15  # Slower wave movement
        if self.wave_offset > 2 * math.pi:
            self.wave_offset = 0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Create pill shape path
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), self.height()//2, self.height()//2)
        
        # Create gradient with glass effect
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        
        if self.status == "listening":
            gradient.setColorAt(0, QColor(41, 128, 185, 230))  # Increased opacity
            gradient.setColorAt(0.5, QColor(52, 152, 219, 230))
            gradient.setColorAt(1, QColor(41, 128, 185, 230))
        elif self.status == "speaking":
            gradient.setColorAt(0, QColor(39, 174, 96, 230))
            gradient.setColorAt(0.5, QColor(46, 204, 113, 230))
            gradient.setColorAt(1, QColor(39, 174, 96, 230))
        else:
            gradient.setColorAt(0, QColor(44, 62, 80, 200))
            gradient.setColorAt(0.5, QColor(52, 73, 94, 200))
            gradient.setColorAt(1, QColor(44, 62, 80, 200))
            
        # Fill background with glass effect
        painter.fillPath(path, gradient)
        
        # Add subtle border with animation
        if self.status in ["listening", "speaking"]:
            glow_color = QColor(52, 152, 219, 150) if self.status == "listening" else QColor(46, 204, 113, 150)
            painter.setPen(QPen(glow_color, 2))
        else:
            painter.setPen(QPen(QColor(52, 152, 219, 100), 1))
        painter.drawPath(path)
        
        # Draw wave animation if listening or speaking
        if self.status in ["listening", "speaking"]:
            painter.setClipPath(path)
            painter.setPen(Qt.PenStyle.NoPen)
            
            # Different wave colors for different states
            if self.status == "listening":
                wave_color = QColor(255, 255, 255, 50)
            else:  # speaking
                wave_color = QColor(255, 255, 255, 60)
            
            wave_height = 15  # Slightly reduced height for subtler effect
            
            for i in range(3):  # Three waves for better performance
                points = []
                offset = self.wave_offset + i * math.pi / 3
                
                # Improved wave calculation
                for x in self.wave_points:
                    # Combined sine waves for more organic movement
                    y = (math.sin(x * 0.03 + offset) * 0.6 + 
                         math.sin(x * 0.02 - offset * 1.5) * 0.4) * wave_height
                    points.append(QPoint(x, int(self.height()/2 + y)))
                
                wave_path = QPainterPath()
                wave_path.moveTo(0, self.height())
                
                # Create smooth wave path
                if points:
                    wave_path.moveTo(points[0].x(), points[0].y())
                    for i in range(1, len(points) - 2, 2):
                        wave_path.quadTo(
                            points[i].x(), points[i].y(),
                            (points[i].x() + points[i + 1].x()) / 2,
                            (points[i].y() + points[i + 1].y()) / 2
                        )
                
                wave_path.lineTo(self.width(), self.height())
                wave_path.lineTo(0, self.height())
                
                painter.fillPath(wave_path, wave_color)

    def animate(self, status):
        """Update status without size animation"""
        if status == self.status:
            return
        
        self.status = status
        
        # Start or stop wave animation based on status
        if status in ["listening", "speaking"]:
            if not self.wave_timer.isActive():
                self.wave_timer.start(30)
        else:
            if self.wave_timer.isActive():
                self.wave_timer.stop()
        
        self.update()  # Trigger repaint