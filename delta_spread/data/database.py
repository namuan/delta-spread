"""SQLite database connection management.

This module provides database connection lifecycle management
and schema initialization for the trades database.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import sqlite3

_APP_NAME = "DeltaSpread"
_DB_FILENAME = "trades.db"


def _get_db_dir() -> Path:
    """Return platform-appropriate database directory."""
    if os.name == "nt":
        # Windows: %APPDATA%/DeltaSpread
        base = os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")
        return Path(base) / _APP_NAME
    if os.uname().sysname == "Darwin":
        # macOS: ~/Library/Application Support/DeltaSpread
        return Path.home() / "Library" / "Application Support" / _APP_NAME
    # Linux/Unix: ~/.config/deltaspread
    xdg = os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
    return Path(xdg) / _APP_NAME.lower()


def get_default_db_path() -> Path:
    """Get the default database file path."""
    return _get_db_dir() / _DB_FILENAME


_SCHEMA_SQL = """
-- Trades table
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    underlier_symbol TEXT NOT NULL,
    underlier_spot REAL NOT NULL,
    underlier_multiplier INTEGER NOT NULL,
    underlier_currency TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    notes TEXT
);

-- Trade legs/positions table
CREATE TABLE IF NOT EXISTS trade_legs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id INTEGER NOT NULL,
    expiry TEXT NOT NULL,
    strike REAL NOT NULL,
    option_type TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    entry_price REAL,
    notes TEXT,
    FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE CASCADE
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_trades_name ON trades(name);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(underlier_symbol);
CREATE INDEX IF NOT EXISTS idx_trade_legs_trade ON trade_legs(trade_id);
"""


class DatabaseConnection:
    """SQLite database connection manager.

    Handles connection creation, schema initialization,
    and proper resource cleanup.
    """

    def __init__(  # pyright: ignore[reportMissingSuperCall]
        self, db_path: Path | None = None
    ) -> None:
        """Initialize database connection.

        Args:
            db_path: Path to database file. If None, uses default app location.
        """
        self._db_path = db_path or get_default_db_path()
        self._connection: sqlite3.Connection | None = None
        self._logger = logging.getLogger(__name__)

    @property
    def db_path(self) -> Path:
        """Get the database file path."""
        return self._db_path

    def get_connection(self) -> sqlite3.Connection:
        """Get the SQLite connection (creates if needed).

        Returns:
            Active SQLite connection with row factory set.
        """
        if self._connection is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(str(self._db_path))
            self._connection.row_factory = sqlite3.Row
            # Enable foreign key enforcement
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._logger.info("Database connection opened: %s", self._db_path)
        return self._connection

    def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            self._connection.close()
            self._connection = None
            self._logger.info("Database connection closed")

    def initialize_schema(self) -> None:
        """Create tables if they don't exist."""
        conn = self.get_connection()
        conn.executescript(_SCHEMA_SQL)
        conn.commit()
        self._logger.info("Database schema initialized")

    def __enter__(self) -> DatabaseConnection:
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Context manager exit - close connection."""
        self.close()
