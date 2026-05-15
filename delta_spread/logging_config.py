"""Logging configuration for DeltaSpread.

Configures a rotating file handler writing to ~/Library/Logs/DeltaSpread/
on macOS (or ~/.local/share/DeltaSpread/logs on Linux) and a console handler.
File logging defaults to DEBUG for verbose diagnostics; console stays at INFO.
"""

from __future__ import annotations

import logging
from logging import DEBUG, INFO, Formatter, StreamHandler, getLogger
from logging.handlers import RotatingFileHandler
from pathlib import Path
import platform
import sys

APP_NAME = "DeltaSpread"
DEFAULT_LOG_FILENAME = "app.log"
MAX_LOG_BYTES = 10_000_000
BACKUP_COUNT = 5

_LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def configure_logging(log_dir: Path | None = None, *, level: int = INFO) -> Path:
    """Configure root logger with console and rotating file handlers.

    The console handler uses the given *level* (default INFO).
    The file handler always writes at DEBUG for full diagnostics.

    Returns the path to the log file used.
    """
    root = getLogger()
    root.setLevel(DEBUG)

    _clear_existing_handlers(root)

    console_handler = StreamHandler(sys.stderr)
    console_handler.setLevel(level)
    console_handler.setFormatter(Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    root.addHandler(console_handler)

    if log_dir is None:
        log_dir = _default_log_dir()

    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / DEFAULT_LOG_FILENAME

    file_handler = RotatingFileHandler(
        str(log_path),
        maxBytes=MAX_LOG_BYTES,
        backupCount=BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(DEBUG)
    file_handler.setFormatter(Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    root.addHandler(file_handler)

    getLogger(__name__).info(
        "Logging initialized → %s (console level=%s)",
        log_path,
        logging.getLevelName(level),
    )
    return log_path


def _default_log_dir() -> Path:
    home = Path.home()
    if platform.system() == "Darwin":
        return home / "Library" / "Logs" / APP_NAME
    return home / ".local" / "share" / APP_NAME / "logs"


def _clear_existing_handlers(root: logging.Logger) -> None:
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
