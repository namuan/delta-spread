import logging
import sys

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

from delta_spread.ui.main_window import MainWindow

from .logging_config import configure_logging

logger = logging.getLogger(__name__)


def main() -> None:
    log_path = configure_logging()
    logger.info("DeltaSpread starting — log file: %s", log_path)

    app = QApplication(sys.argv)
    families = QFontDatabase.families()
    candidates = ["Segoe UI", "Helvetica Neue", "Arial", "Noto Sans", "DejaVu Sans"]
    for family in candidates:
        if family in families:
            app.setFont(QFont(family, 9))
            logger.debug("Font selected: %s", family)
            break

    logger.info("Creating main window")
    window = MainWindow()
    window.show()
    logger.info("Main window shown — entering event loop")
    sys.exit(app.exec())
