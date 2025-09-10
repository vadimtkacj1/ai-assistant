import sys
import ctypes
from PyQt6.QtWidgets import QApplication
from MainWindow import MainWindow

if __name__ == '__main__':
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI
    except Exception:
        pass  # Qt will handle DPI awareness by default

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 