import sys

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

from .ui.main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    families = QFontDatabase.families()
    candidates = ["Segoe UI", "Helvetica Neue", "Arial", "Noto Sans", "DejaVu Sans"]
    for family in candidates:
        if family in families:
            app.setFont(QFont(family, 9))
            break
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
