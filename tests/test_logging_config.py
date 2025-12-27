import contextlib
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from delta_spread.logging_config import configure_logging


def test_configure_logging_writes_file(tmp_path: Path):
    log_dir = tmp_path / "logs"
    log_path = log_dir / "app.log"

    # Ensure no handlers from previous tests
    root = logging.getLogger()
    existing_handlers = list(root.handlers)
    for h in existing_handlers:
        root.removeHandler(h)
        with contextlib.suppress(Exception):
            h.close()

    # Configure logging to use tmp path
    returned = configure_logging(log_dir)
    assert returned == log_path

    logger = logging.getLogger("delta_spread.tests")
    logger.info("test message for logging")

    # File should exist and contain our message
    assert log_path.exists(), f"Expected log file at {log_path}"
    content = log_path.read_text(encoding="utf-8")
    assert "test message for logging" in content

    # Ensure a RotatingFileHandler was added for our file
    assert any(
        isinstance(h, RotatingFileHandler)
        and getattr(h, "baseFilename", None) == str(log_path)
        for h in logging.getLogger().handlers
    )

    # Cleanup handlers
    for h in list(logging.getLogger().handlers):
        logging.getLogger().removeHandler(h)
        with contextlib.suppress(Exception):
            h.close()
    for h in existing_handlers:
        logging.getLogger().addHandler(h)
