"""Trade repository for SQLite persistence.

This module provides CRUD operations for saving and loading trades
to/from the SQLite database.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import logging
from typing import TYPE_CHECKING, Protocol, TypedDict, cast

from ..domain.models import (
    OptionContract,
    OptionLeg,
    OptionType,
    Side,
    Strategy,
    Underlier,
)

if TYPE_CHECKING:
    import sqlite3

    from .database import DatabaseConnection


class _TradeRow(TypedDict):
    """Type definition for trade table rows."""

    id: int
    name: str
    underlier_symbol: str
    underlier_spot: float
    underlier_multiplier: int
    underlier_currency: str
    created_at: str
    updated_at: str
    notes: str | None


class _LegRow(TypedDict):
    """Type definition for trade_legs table rows."""

    id: int
    trade_id: int
    expiry: str
    strike: float
    option_type: str
    side: str
    quantity: int
    entry_price: float | None
    notes: str | None


class _TradeSummaryRow(TypedDict):
    """Type definition for trade summary query result."""

    id: int
    name: str
    underlier_symbol: str
    leg_count: int
    created_at: str
    updated_at: str
    notes: str | None


@dataclass
class TradeSummary:
    """Lightweight trade summary for list views."""

    id: int
    name: str
    underlier_symbol: str
    leg_count: int
    created_at: datetime
    updated_at: datetime
    notes: str | None


class TradeRepositoryProtocol(Protocol):
    """Protocol for trade persistence operations."""

    def save(self, trade: Strategy, name: str, notes: str | None = None) -> int:
        """Save a trade to the database."""
        ...

    def update(self, trade_id: int, trade: Strategy, notes: str | None = None) -> None:
        """Update an existing trade."""
        ...

    def delete(self, trade_id: int) -> None:
        """Delete a trade and its legs."""
        ...

    def get_by_id(self, trade_id: int) -> tuple[Strategy, str | None] | None:
        """Retrieve a trade by its database ID."""
        ...

    def get_by_name(self, name: str) -> tuple[Strategy, str | None] | None:
        """Retrieve a trade by its name."""
        ...

    def list_all(self) -> list[TradeSummary]:
        """List all saved trades."""
        ...

    def list_by_symbol(self, symbol: str) -> list[TradeSummary]:
        """List trades for a specific symbol."""
        ...

    def name_exists(self, name: str) -> bool:
        """Check if a trade name already exists."""
        ...


class TradeRepository:
    """SQLite implementation of trade repository.

    Handles serialization/deserialization of Strategy domain
    models to/from SQLite database as trades.
    """

    def __init__(  # pyright: ignore[reportMissingSuperCall]
        self, db: DatabaseConnection
    ) -> None:
        """Initialize repository with database connection.

        Args:
            db: Database connection manager.
        """
        self._db = db
        self._logger = logging.getLogger(__name__)

    def save(self, trade: Strategy, name: str, notes: str | None = None) -> int:
        """Save a trade to the database.

        Args:
            trade: The strategy/positions to save as a trade.
            name: Name for the trade.
            notes: Optional notes about the trade.

        Returns:
            The database ID of the saved trade.

        Raises:
            ValueError: If trade name already exists.
        """
        if self.name_exists(name):
            raise ValueError(f"Trade name '{name}' already exists")

        conn = self._db.get_connection()
        now = datetime.now().isoformat()

        cursor = conn.execute(
            """
            INSERT INTO trades (
                name, underlier_symbol, underlier_spot,
                underlier_multiplier, underlier_currency,
                created_at, updated_at, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                trade.underlier.symbol,
                trade.underlier.spot,
                trade.underlier.multiplier,
                trade.underlier.currency,
                now,
                now,
                notes,
            ),
        )
        trade_id = cursor.lastrowid
        if trade_id is None:
            raise ValueError("Failed to insert trade")

        self._insert_legs(trade_id, trade.legs)
        conn.commit()

        self._logger.info("Saved trade '%s' with ID %d", name, trade_id)
        return trade_id

    def update(self, trade_id: int, trade: Strategy, notes: str | None = None) -> None:
        """Update an existing trade.

        Args:
            trade_id: Database ID of trade to update.
            trade: New trade data.
            notes: Optional notes about the trade.

        Raises:
            ValueError: If trade_id not found.
        """
        conn = self._db.get_connection()
        now = datetime.now().isoformat()

        cursor = conn.execute(
            """
            UPDATE trades SET
                underlier_symbol = ?,
                underlier_spot = ?,
                underlier_multiplier = ?,
                underlier_currency = ?,
                updated_at = ?,
                notes = ?
            WHERE id = ?
            """,
            (
                trade.underlier.symbol,
                trade.underlier.spot,
                trade.underlier.multiplier,
                trade.underlier.currency,
                now,
                notes,
                trade_id,
            ),
        )

        if cursor.rowcount == 0:
            raise ValueError(f"Trade with ID {trade_id} not found")

        # Delete existing legs and insert new ones
        conn.execute("DELETE FROM trade_legs WHERE trade_id = ?", (trade_id,))
        self._insert_legs(trade_id, trade.legs)
        conn.commit()

        self._logger.info("Updated trade ID %d", trade_id)

    def delete(self, trade_id: int) -> None:
        """Delete a trade and its legs.

        Args:
            trade_id: Database ID of trade to delete.
        """
        conn = self._db.get_connection()
        conn.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
        conn.commit()
        self._logger.info("Deleted trade ID %d", trade_id)

    def get_by_id(self, trade_id: int) -> tuple[Strategy, str | None] | None:
        """Retrieve a trade by its database ID.

        Args:
            trade_id: Database ID to look up.

        Returns:
            Tuple of (Strategy, notes) if found, None otherwise.
        """
        conn = self._db.get_connection()
        cursor = conn.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
        row: sqlite3.Row | None = cursor.fetchone()  # pyright: ignore[reportAny]

        if row is None:
            return None

        return self._deserialize_trade(cast("_TradeRow", dict(row)))

    def get_by_name(self, name: str) -> tuple[Strategy, str | None] | None:
        """Retrieve a trade by its name.

        Args:
            name: Trade name to look up.

        Returns:
            Tuple of (Strategy, notes) if found, None otherwise.
        """
        conn = self._db.get_connection()
        cursor = conn.execute("SELECT * FROM trades WHERE name = ?", (name,))
        row: sqlite3.Row | None = cursor.fetchone()  # pyright: ignore[reportAny]

        if row is None:
            return None

        return self._deserialize_trade(cast("_TradeRow", dict(row)))

    def list_all(self) -> list[TradeSummary]:
        """List all saved trades.

        Returns:
            List of trade summaries, ordered by updated_at descending.
        """
        conn = self._db.get_connection()
        cursor = conn.execute(
            """
            SELECT t.*, COUNT(tl.id) as leg_count
            FROM trades t
            LEFT JOIN trade_legs tl ON t.id = tl.trade_id
            GROUP BY t.id
            ORDER BY t.updated_at DESC
            """
        )
        rows: list[sqlite3.Row] = cursor.fetchall()

        return [
            self._row_to_summary(cast("_TradeSummaryRow", dict(row))) for row in rows
        ]

    def list_by_symbol(self, symbol: str) -> list[TradeSummary]:
        """List trades for a specific symbol.

        Args:
            symbol: Underlier symbol to filter by.

        Returns:
            List of trade summaries for the symbol.
        """
        conn = self._db.get_connection()
        cursor = conn.execute(
            """
            SELECT t.*, COUNT(tl.id) as leg_count
            FROM trades t
            LEFT JOIN trade_legs tl ON t.id = tl.trade_id
            WHERE t.underlier_symbol = ?
            GROUP BY t.id
            ORDER BY t.updated_at DESC
            """,
            (symbol,),
        )
        rows: list[sqlite3.Row] = cursor.fetchall()

        return [
            self._row_to_summary(cast("_TradeSummaryRow", dict(row))) for row in rows
        ]

    def name_exists(self, name: str) -> bool:
        """Check if a trade name already exists.

        Args:
            name: Name to check.

        Returns:
            True if name exists, False otherwise.
        """
        conn = self._db.get_connection()
        row = conn.execute(  # pyright: ignore[reportAny]
            "SELECT 1 FROM trades WHERE name = ?", (name,)
        ).fetchone()
        return row is not None

    def _insert_legs(self, trade_id: int, legs: list[OptionLeg]) -> None:
        """Insert legs for a trade.

        Args:
            trade_id: Database ID of the parent trade.
            legs: List of option legs to insert.
        """
        conn = self._db.get_connection()
        for leg in legs:
            conn.execute(
                """
                INSERT INTO trade_legs (
                    trade_id, expiry, strike, option_type,
                    side, quantity, entry_price, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trade_id,
                    leg.contract.expiry.isoformat(),
                    leg.contract.strike,
                    leg.contract.type.value,
                    leg.side.value,
                    leg.quantity,
                    leg.entry_price,
                    leg.notes,
                ),
            )

    def _deserialize_trade(self, row: _TradeRow) -> tuple[Strategy, str | None]:
        """Deserialize a database row into a Strategy.

        Args:
            row: Typed trade row dict.

        Returns:
            Tuple of (Strategy, notes).
        """
        trade_id = row["id"]
        underlier = Underlier(
            symbol=row["underlier_symbol"],
            spot=row["underlier_spot"],
            multiplier=row["underlier_multiplier"],
            currency=row["underlier_currency"],
        )

        conn = self._db.get_connection()
        cursor = conn.execute(
            "SELECT * FROM trade_legs WHERE trade_id = ?", (trade_id,)
        )
        leg_rows: list[sqlite3.Row] = cursor.fetchall()

        legs = [
            self._deserialize_leg(cast("_LegRow", dict(leg_row)), underlier)
            for leg_row in leg_rows
        ]

        strategy = Strategy(
            name=row["name"],
            underlier=underlier,
            legs=legs,
            created_at=datetime.fromisoformat(row["created_at"]),
        )

        return strategy, row["notes"]

    @staticmethod
    def _deserialize_leg(row: _LegRow, underlier: Underlier) -> OptionLeg:
        """Deserialize a database row into an OptionLeg.

        Args:
            row: Typed leg row dict.
            underlier: The underlier for the contract.

        Returns:
            OptionLeg instance.
        """
        contract = OptionContract(
            underlier=underlier,
            expiry=date.fromisoformat(row["expiry"]),
            strike=row["strike"],
            type=OptionType(row["option_type"]),
        )
        return OptionLeg(
            contract=contract,
            side=Side(row["side"]),
            quantity=row["quantity"],
            entry_price=row["entry_price"],
            notes=row["notes"],
        )

    @staticmethod
    def _row_to_summary(row: _TradeSummaryRow) -> TradeSummary:
        """Convert a database row to a TradeSummary.

        Args:
            row: Typed summary row dict with leg_count.

        Returns:
            TradeSummary instance.
        """
        return TradeSummary(
            id=row["id"],
            name=row["name"],
            underlier_symbol=row["underlier_symbol"],
            leg_count=row["leg_count"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            notes=row["notes"],
        )
