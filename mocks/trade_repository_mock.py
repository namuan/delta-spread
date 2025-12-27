"""Mock trade repository for testing.

Provides an in-memory implementation of TradeRepository for unit tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from delta_spread.data.trade_repository import TradeSummary
from delta_spread.domain.models import Strategy


@dataclass
class StoredTrade:
    """Internal representation of a stored trade."""

    strategy: Strategy
    name: str
    notes: str | None
    created_at: datetime
    updated_at: datetime


class MockTradeRepository:
    """In-memory mock for testing without SQLite.

    Implements TradeRepositoryProtocol for use in unit tests.
    """

    def __init__(self) -> None:
        """Initialize the mock repository."""
        self._trades: dict[int, StoredTrade] = {}
        self._next_id = 1

    def save(self, trade: Strategy, name: str, notes: str | None = None) -> int:
        """Save a trade to the in-memory store.

        Args:
            trade: The strategy/positions to save.
            name: Name for the trade.
            notes: Optional notes about the trade.

        Returns:
            The ID of the saved trade.

        Raises:
            ValueError: If trade name already exists.
        """
        if self.name_exists(name):
            raise ValueError(f"Trade name '{name}' already exists")

        trade_id = self._next_id
        self._next_id += 1

        now = datetime.now()
        self._trades[trade_id] = StoredTrade(
            strategy=trade,
            name=name,
            notes=notes,
            created_at=now,
            updated_at=now,
        )

        return trade_id

    def update(self, trade_id: int, trade: Strategy, notes: str | None = None) -> None:
        """Update an existing trade.

        Args:
            trade_id: ID of trade to update.
            trade: New trade data.
            notes: Optional notes about the trade.

        Raises:
            ValueError: If trade_id not found.
        """
        if trade_id not in self._trades:
            raise ValueError(f"Trade with ID {trade_id} not found")

        stored = self._trades[trade_id]
        self._trades[trade_id] = StoredTrade(
            strategy=trade,
            name=stored.name,
            notes=notes,
            created_at=stored.created_at,
            updated_at=datetime.now(),
        )

    def delete(self, trade_id: int) -> None:
        """Delete a trade.

        Args:
            trade_id: ID of trade to delete.
        """
        self._trades.pop(trade_id, None)

    def get_by_id(self, trade_id: int) -> tuple[Strategy, str | None] | None:
        """Retrieve a trade by its ID.

        Args:
            trade_id: ID to look up.

        Returns:
            Tuple of (Strategy, notes) if found, None otherwise.
        """
        stored = self._trades.get(trade_id)
        if stored is None:
            return None
        # Reconstruct Strategy with saved name
        strategy = Strategy(
            name=stored.name,
            underlier=stored.strategy.underlier,
            legs=stored.strategy.legs,
            created_at=stored.created_at,
        )
        return strategy, stored.notes

    def get_by_name(self, name: str) -> tuple[Strategy, str | None] | None:
        """Retrieve a trade by its name.

        Args:
            name: Trade name to look up.

        Returns:
            Tuple of (Strategy, notes) if found, None otherwise.
        """
        for stored in self._trades.values():
            if stored.name == name:
                # Reconstruct Strategy with saved name
                strategy = Strategy(
                    name=stored.name,
                    underlier=stored.strategy.underlier,
                    legs=stored.strategy.legs,
                    created_at=stored.created_at,
                )
                return strategy, stored.notes
        return None

    def list_all(self) -> list[TradeSummary]:
        """List all saved trades.

        Returns:
            List of trade summaries, ordered by updated_at descending.
        """
        summaries = [
            TradeSummary(
                id=trade_id,
                name=stored.name,
                underlier_symbol=stored.strategy.underlier.symbol,
                leg_count=len(stored.strategy.legs),
                created_at=stored.created_at,
                updated_at=stored.updated_at,
                notes=stored.notes,
            )
            for trade_id, stored in self._trades.items()
        ]
        return sorted(summaries, key=lambda s: s.updated_at, reverse=True)

    def list_by_symbol(self, symbol: str) -> list[TradeSummary]:
        """List trades for a specific symbol.

        Args:
            symbol: Underlier symbol to filter by.

        Returns:
            List of trade summaries for the symbol.
        """
        all_trades = self.list_all()
        return [t for t in all_trades if t.underlier_symbol == symbol]

    def name_exists(self, name: str) -> bool:
        """Check if a trade name already exists.

        Args:
            name: Name to check.

        Returns:
            True if name exists, False otherwise.
        """
        return any(stored.name == name for stored in self._trades.values())

    def clear(self) -> None:
        """Clear all stored trades (useful for test setup)."""
        self._trades.clear()
        self._next_id = 1
