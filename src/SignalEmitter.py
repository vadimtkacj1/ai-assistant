from PyQt6.QtCore import (pyqtSignal, QObject)

class SignalEmitter(QObject):
    status_changed = pyqtSignal(str)
    animation_trigger = pyqtSignal(str)
    new_message = pyqtSignal(str, bool)  # message, is_user