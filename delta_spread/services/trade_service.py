"""Trade management service.

This module provides business logic for saving and loading trades,
coordinating between the UI and repository layers.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol

_MAX_NAME_LENGTH = 100

if TYPE_CHECKING:
    from ..data.trade_repository import TradeRepositoryProtocol, TradeSummary
    from ..domain.models import Strategy


class TradeServiceProtocol(Protocol):
    """Protocol for trade management service."""

    def save_trade(
        self,
        trade: Strategy,
        name: str,
        notes: str | None = None,
    ) -> int:
        """Save positions as a trade."""
        ...

    def update_trade(
        self,
        trade_id: int,
        trade: Strategy,
        notes: str | None = None,
    ) -> None:
        """Update an existing trade."""
        ...

    def load_trade(self, trade_id: int) -> Strategy | None:
        """Load a saved trade."""
        ...

    def delete_trade(self, trade_id: int) -> None:
        """Delete a saved trade."""
        ...

    def get_saved_trades(self) -> list[TradeSummary]:
        """Get list of all saved trades."""
        ...

    def trade_name_exists(self, name: str) -> bool:
        """Check if a trade name is already in use."""
        ...


class TradeService:
    """Service for managing saved trades.

    Provides high-level operations for saving and loading
    trades, with validation and business rules.
    """

    def __init__(  # pyright: ignore[reportMissingSuperCall]
        self, repository: TradeRepositoryProtocol
    ) -> None:
        """Initialize service with repository dependency.

        Args:
            repository: Trade repository for persistence.
        """
        self._repository = repository
        self._logger = logging.getLogger(__name__)

    def save_trade(
        self,
        trade: Strategy,
        name: str,
        notes: str | None = None,
    ) -> int:
        """Save the current positions as a trade.

        Args:
            trade: Strategy containing positions to save.
            name: Name for the trade.
            notes: Optional notes about the trade.

        Returns:
            Database ID of saved trade.

        Raises:
            ValueError: If name already exists, is empty, or trade is invalid.
        """
        # Validate name
        name = name.strip()
        if not name:
            raise ValueError("Trade name cannot be empty")

        if len(name) > _MAX_NAME_LENGTH:
            raise ValueError(
                f"Trade name must be {_MAX_NAME_LENGTH} characters or less"
            )

        # Validate trade has legs
        if not trade.legs:
            raise ValueError("Trade must have at least one leg")

        self._logger.info("Saving trade '%s' with %d legs", name, len(trade.legs))
        return self._repository.save(trade, name, notes)

    def update_trade(
        self,
        trade_id: int,
        trade: Strategy,
        notes: str | None = None,
    ) -> None:
        """Update an existing trade.

        Args:
            trade_id: ID of trade to update.
            trade: Strategy containing updated positions.
            notes: Optional notes about the trade.

        Raises:
            ValueError: If trade_id not found or trade is invalid.
        """
        # Validate trade has legs
        if not trade.legs:
            raise ValueError("Trade must have at least one leg")

        self._logger.info(
            "Updating trade ID %d with %d legs", trade_id, len(trade.legs)
        )
        self._repository.update(trade_id, trade, notes)

    def load_trade(self, trade_id: int) -> Strategy | None:
        """Load a saved trade.

        Args:
            trade_id: ID of trade to load.

        Returns:
            The trade as Strategy if found, None otherwise.
        """
        result = self._repository.get_by_id(trade_id)
        if result is None:
            self._logger.warning("Trade with ID %d not found", trade_id)
            return None

        strategy, _notes = result
        self._logger.info(
            "Loaded trade '%s' with %d legs",
            strategy.name,
            len(strategy.legs),
        )
        return strategy

    def delete_trade(self, trade_id: int) -> None:
        """Delete a saved trade.

        Args:
            trade_id: ID of trade to delete.
        """
        self._repository.delete(trade_id)
        self._logger.info("Deleted trade ID %d", trade_id)

    def get_saved_trades(self) -> list[TradeSummary]:
        """Get list of all saved trades.

        Returns:
            List of trade summaries, ordered by most recent first.
        """
        return self._repository.list_all()

    def trade_name_exists(self, name: str) -> bool:
        """Check if a trade name is already in use.

        Args:
            name: Name to check.

        Returns:
            True if name exists, False otherwise.
        """
        return self._repository.name_exists(name.strip())
