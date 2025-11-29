import logging
import sys

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

from delta_spread.ui.main_window import MainWindow


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
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
