"""Logging configuration helper for DeltaSpread.

This module provides configure_logging to add a RotatingFileHandler
and set up the root logger without importing GUI packages.
"""

from __future__ import annotations

import logging
from logging import INFO, Formatter, basicConfig, getLogger
from logging.handlers import RotatingFileHandler
from pathlib import Path
import platform

APP_NAME = "DeltaSpread"
DEFAULT_LOG_FILENAME = "app.log"


def configure_logging(log_dir: Path | None = None, *, level: int = INFO) -> Path:
    """Configure root logger and add a RotatingFileHandler.

    Returns the path to the log file used.
    """
    # Basic config for console/stderr
    basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if log_dir is None:
        # Default to macOS logs location; fall back to home/.local/share/<app>/logs on other systems
        home = Path.home()

        if platform.system() == "Darwin":
            log_dir = home / "Library" / "Logs" / APP_NAME
        else:
            log_dir = home / ".local" / "share" / APP_NAME / "logs"

    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / DEFAULT_LOG_FILENAME

    # Avoid adding duplicate handlers for the same file
    root = getLogger()
    for h in list(root.handlers):
        if isinstance(h, RotatingFileHandler) and getattr(
            h, "baseFilename", None
        ) == str(log_path):
            return log_path

    handler = RotatingFileHandler(str(log_path), maxBytes=5_000_000, backupCount=3)
    handler.setLevel(level)
    handler.setFormatter(
        Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s", datefmt="%H:%M:%S")
    )
    root.addHandler(handler)

    # Ensure root logger level isn't higher than requested
    root.setLevel(min(root.level, level) if root.level else level)

    logging.getLogger(__name__).info("Logging initialized; writing to %s", log_path)
    return log_path
