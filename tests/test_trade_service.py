"""Tests for trade service."""

from __future__ import annotations

from datetime import date

import pytest

from delta_spread.domain.models import (
    OptionContract,
    OptionLeg,
    OptionType,
    Side,
    Strategy,
    Underlier,
)
from delta_spread.services.trade_service import TradeService
from mocks.trade_repository_mock import MockTradeRepository


@pytest.fixture
def mock_repository() -> MockTradeRepository:
    """Create a mock repository for testing."""
    return MockTradeRepository()


@pytest.fixture
def trade_service(mock_repository: MockTradeRepository) -> TradeService:
    """Create a trade service with mock repository."""
    return TradeService(mock_repository)


@pytest.fixture
def sample_strategy() -> Strategy:
    """Create a sample strategy for testing."""
    underlier = Underlier(
        symbol="SPY",
        spot=450.0,
        multiplier=100,
        currency="USD",
    )
    contract = OptionContract(
        underlier=underlier,
        expiry=date(2024, 3, 15),
        strike=455.0,
        type=OptionType.CALL,
    )
    leg = OptionLeg(
        contract=contract,
        side=Side.BUY,
        quantity=1,
        entry_price=5.50,
    )
    return Strategy(
        name="Test Strategy",
        underlier=underlier,
        legs=[leg],
    )


class TestTradeService:
    """Tests for TradeService."""

    def test_save_trade(
        self, trade_service: TradeService, sample_strategy: Strategy
    ) -> None:
        """Test saving a trade."""
        trade_id = trade_service.save_trade(sample_strategy, "My Trade")

        assert trade_id == 1

        # Verify it can be loaded
        loaded = trade_service.load_trade(trade_id)
        assert loaded is not None
        assert loaded.underlier.symbol == "SPY"

    def test_save_trade_with_notes(
        self, trade_service: TradeService, sample_strategy: Strategy
    ) -> None:
        """Test saving a trade with notes."""
        trade_service.save_trade(
            sample_strategy, "Trade with Notes", notes="Important notes"
        )

        trades = trade_service.get_saved_trades()
        assert len(trades) == 1
        assert trades[0].notes == "Important notes"

    def test_save_trade_empty_name_raises(
        self, trade_service: TradeService, sample_strategy: Strategy
    ) -> None:
        """Test that empty name raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            trade_service.save_trade(sample_strategy, "")

        with pytest.raises(ValueError, match="cannot be empty"):
            trade_service.save_trade(sample_strategy, "   ")

    def test_save_trade_long_name_raises(
        self, trade_service: TradeService, sample_strategy: Strategy
    ) -> None:
        """Test that overly long name raises error."""
        long_name = "x" * 101
        with pytest.raises(ValueError, match="100 characters"):
            trade_service.save_trade(sample_strategy, long_name)

    def test_save_trade_duplicate_name_raises(
        self, trade_service: TradeService, sample_strategy: Strategy
    ) -> None:
        """Test that duplicate name raises error."""
        trade_service.save_trade(sample_strategy, "Unique Name")

        with pytest.raises(ValueError, match="already exists"):
            trade_service.save_trade(sample_strategy, "Unique Name")

    def test_load_trade(
        self, trade_service: TradeService, sample_strategy: Strategy
    ) -> None:
        """Test loading a trade."""
        trade_id = trade_service.save_trade(sample_strategy, "To Load")

        loaded = trade_service.load_trade(trade_id)

        assert loaded is not None
        assert loaded.name == "To Load"
        assert len(loaded.legs) == 1

    def test_load_nonexistent_trade(self, trade_service: TradeService) -> None:
        """Test loading non-existent trade returns None."""
        loaded = trade_service.load_trade(9999)
        assert loaded is None

    def test_delete_trade(
        self, trade_service: TradeService, sample_strategy: Strategy
    ) -> None:
        """Test deleting a trade."""
        trade_id = trade_service.save_trade(sample_strategy, "To Delete")

        trade_service.delete_trade(trade_id)

        loaded = trade_service.load_trade(trade_id)
        assert loaded is None

    def test_get_saved_trades(
        self, trade_service: TradeService, sample_strategy: Strategy
    ) -> None:
        """Test getting list of saved trades."""
        trade_service.save_trade(sample_strategy, "Trade 1")
        trade_service.save_trade(sample_strategy, "Trade 2")

        trades = trade_service.get_saved_trades()

        assert len(trades) == 2
        names = {t.name for t in trades}
        assert names == {"Trade 1", "Trade 2"}

    def test_trade_name_exists(
        self, trade_service: TradeService, sample_strategy: Strategy
    ) -> None:
        """Test checking if trade name exists."""
        assert not trade_service.trade_name_exists("New Trade")

        trade_service.save_trade(sample_strategy, "New Trade")

        assert trade_service.trade_name_exists("New Trade")
        assert trade_service.trade_name_exists("  New Trade  ")  # Trimmed
        assert not trade_service.trade_name_exists("Other Trade")

    def test_save_trade_strips_whitespace(
        self, trade_service: TradeService, sample_strategy: Strategy
    ) -> None:
        """Test that trade name whitespace is stripped."""
        trade_id = trade_service.save_trade(sample_strategy, "  Trimmed Name  ")

        loaded = trade_service.load_trade(trade_id)
        assert loaded is not None
        # Name should be stored trimmed
        trades = trade_service.get_saved_trades()
        assert trades[0].name == "Trimmed Name"

    def test_update_trade(
        self, trade_service: TradeService, sample_strategy: Strategy
    ) -> None:
        """Test updating an existing trade."""
        trade_id = trade_service.save_trade(sample_strategy, "Original")

        # Create an updated strategy with different legs
        updated_leg = sample_strategy.legs[0].model_copy(update={"quantity": 5})
        updated_strategy = sample_strategy.model_copy(update={"legs": [updated_leg]})

        trade_service.update_trade(trade_id, updated_strategy, notes="Updated notes")

        loaded = trade_service.load_trade(trade_id)
        assert loaded is not None
        assert loaded.legs[0].quantity == 5

    def test_update_trade_nonexistent_raises(
        self, trade_service: TradeService, sample_strategy: Strategy
    ) -> None:
        """Test updating non-existent trade raises error."""
        with pytest.raises(ValueError, match="not found"):
            trade_service.update_trade(9999, sample_strategy)
