from PyQt6.QtWidgets import (QVBoxLayout, QLabel, QFrame,
                           QGraphicsOpacityEffect)
from PyQt6.QtCore import (QPropertyAnimation, QEasingCurve, 
                         QParallelAnimationGroup)

class ChatBubble(QFrame):
    def __init__(self, text, is_user=False, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self.setObjectName("userBubble" if is_user else "assistantBubble")
        
        # Add fade-in effect
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(0)
        
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(150)  # Faster animation
        self.fade_animation.setStartValue(0)
        self.fade_animation.setEndValue(1)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Add slide-in effect
        self.slide_animation = QPropertyAnimation(self, b"geometry")
        self.slide_animation.setDuration(150)  # Faster animation
        self.slide_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # Combine animations
        self.animation_group = QParallelAnimationGroup()
        self.animation_group.addAnimation(self.fade_animation)
        self.animation_group.addAnimation(self.slide_animation)
        
        # Setup UI
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(0)  # Reduce spacing
        
        message = QLabel(text)
        message.setWordWrap(True)
        message.setStyleSheet("""
            QLabel {
                color: #ffffff;
                background: transparent;
                font-size: 14px;
                line-height: 1.4;
            }
        """)
        layout.addWidget(message)
        
        # Style the bubble with glass effect
        self.setStyleSheet(f"""
            QFrame#userBubble {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(41, 128, 185, 0.8),
                    stop:1 rgba(52, 152, 219, 0.8));
                border-radius: 15px;
                border: 1px solid rgba(52, 152, 219, 0.3);
                margin-left: 50px;
                margin-right: 10px;
            }}
            QFrame#assistantBubble {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(44, 62, 80, 0.6),
                    stop:1 rgba(52, 73, 94, 0.6));
                border-radius: 15px;
                border: 1px solid rgba(52, 152, 219, 0.3);
                margin-left: 10px;
                margin-right: 50px;
            }}
        """)

    def showEvent(self, event):
        super().showEvent(event)
        # Setup slide animation
        start_geo = self.geometry()
        if self.is_user:
            start_geo.moveRight(start_geo.right() + 50)
        else:
            start_geo.moveLeft(start_geo.left() - 50)
        
        self.slide_animation.setStartValue(start_geo)
        self.slide_animation.setEndValue(self.geometry())
        
        # Start animation group
        self.animation_group.start()