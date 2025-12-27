import sys

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

from delta_spread.ui.main_window import MainWindow

from .logging_config import configure_logging


def main() -> None:
    # Configure logging (adds a rotating file handler writing to ~/Library/Logs/DeltaSpread/app.log on macOS)
    configure_logging()

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
