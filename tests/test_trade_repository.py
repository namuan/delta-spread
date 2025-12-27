"""Tests for trade repository."""

from __future__ import annotations

from datetime import date
from pathlib import Path
import tempfile

import pytest

from delta_spread.data.database import DatabaseConnection
from delta_spread.data.trade_repository import TradeRepository
from delta_spread.domain.models import (
    OptionContract,
    OptionLeg,
    OptionType,
    Side,
    Strategy,
    Underlier,
)


@pytest.fixture
def db_connection() -> DatabaseConnection:
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_trades.db"
        db = DatabaseConnection(db_path)
        db.initialize_schema()
        yield db
        db.close()


@pytest.fixture
def repository(db_connection: DatabaseConnection) -> TradeRepository:
    """Create a repository with the test database."""
    return TradeRepository(db_connection)


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


@pytest.fixture
def multi_leg_strategy() -> Strategy:
    """Create a multi-leg strategy for testing."""
    underlier = Underlier(
        symbol="AAPL",
        spot=180.0,
        multiplier=100,
        currency="USD",
    )
    call_contract = OptionContract(
        underlier=underlier,
        expiry=date(2024, 4, 19),
        strike=185.0,
        type=OptionType.CALL,
    )
    put_contract = OptionContract(
        underlier=underlier,
        expiry=date(2024, 4, 19),
        strike=175.0,
        type=OptionType.PUT,
    )
    call_leg = OptionLeg(
        contract=call_contract,
        side=Side.BUY,
        quantity=2,
        entry_price=3.25,
    )
    put_leg = OptionLeg(
        contract=put_contract,
        side=Side.SELL,
        quantity=1,
        entry_price=2.10,
    )
    return Strategy(
        name="Iron Condor",
        underlier=underlier,
        legs=[call_leg, put_leg],
    )


class TestTradeRepository:
    """Tests for TradeRepository."""

    def test_save_and_retrieve_trade(
        self, repository: TradeRepository, sample_strategy: Strategy
    ) -> None:
        """Test round-trip save and load."""
        trade_id = repository.save(sample_strategy, "My Trade", "Test notes")

        result = repository.get_by_id(trade_id)
        assert result is not None

        loaded_strategy, notes = result
        assert loaded_strategy.name == "My Trade"
        assert loaded_strategy.underlier.symbol == "SPY"
        assert loaded_strategy.underlier.spot == 450.0
        assert len(loaded_strategy.legs) == 1
        assert loaded_strategy.legs[0].contract.strike == 455.0
        assert loaded_strategy.legs[0].side == Side.BUY
        assert notes == "Test notes"

    def test_save_duplicate_name_raises(
        self, repository: TradeRepository, sample_strategy: Strategy
    ) -> None:
        """Test unique name constraint."""
        repository.save(sample_strategy, "Unique Name")

        with pytest.raises(ValueError, match="already exists"):
            repository.save(sample_strategy, "Unique Name")

    def test_get_by_name(
        self, repository: TradeRepository, sample_strategy: Strategy
    ) -> None:
        """Test retrieval by name."""
        repository.save(sample_strategy, "Named Trade")

        result = repository.get_by_name("Named Trade")
        assert result is not None

        loaded_strategy, _ = result
        assert loaded_strategy.underlier.symbol == "SPY"

    def test_get_by_name_not_found(self, repository: TradeRepository) -> None:
        """Test retrieval by name when not found."""
        result = repository.get_by_name("Nonexistent")
        assert result is None

    def test_delete_trade(
        self, repository: TradeRepository, sample_strategy: Strategy
    ) -> None:
        """Test trade deletion."""
        trade_id = repository.save(sample_strategy, "To Delete")

        repository.delete(trade_id)

        result = repository.get_by_id(trade_id)
        assert result is None

    def test_delete_cascades_legs(
        self, repository: TradeRepository, multi_leg_strategy: Strategy
    ) -> None:
        """Test legs are deleted with trade."""
        trade_id = repository.save(multi_leg_strategy, "Multi Leg")

        # Verify legs exist
        result = repository.get_by_id(trade_id)
        assert result is not None
        strategy, _ = result
        assert len(strategy.legs) == 2

        # Delete and verify
        repository.delete(trade_id)
        result = repository.get_by_id(trade_id)
        assert result is None

    def test_list_all_trades(
        self,
        repository: TradeRepository,
        sample_strategy: Strategy,
        multi_leg_strategy: Strategy,
    ) -> None:
        """Test listing all trades."""
        repository.save(sample_strategy, "Trade 1")
        repository.save(multi_leg_strategy, "Trade 2")

        trades = repository.list_all()

        assert len(trades) == 2
        names = {t.name for t in trades}
        assert names == {"Trade 1", "Trade 2"}

    def test_list_trades_ordered_by_date(
        self, repository: TradeRepository, sample_strategy: Strategy
    ) -> None:
        """Test listing returns newest first."""
        repository.save(sample_strategy, "First")
        repository.save(sample_strategy, "Second")
        repository.save(sample_strategy, "Third")

        trades = repository.list_all()

        # Most recently updated should be first
        assert trades[0].name == "Third"
        assert trades[-1].name == "First"

    def test_list_by_symbol(
        self,
        repository: TradeRepository,
        sample_strategy: Strategy,
        multi_leg_strategy: Strategy,
    ) -> None:
        """Test filtering trades by symbol."""
        repository.save(sample_strategy, "SPY Trade")
        repository.save(multi_leg_strategy, "AAPL Trade")

        spy_trades = repository.list_by_symbol("SPY")
        aapl_trades = repository.list_by_symbol("AAPL")

        assert len(spy_trades) == 1
        assert spy_trades[0].name == "SPY Trade"

        assert len(aapl_trades) == 1
        assert aapl_trades[0].name == "AAPL Trade"

    def test_name_exists(
        self, repository: TradeRepository, sample_strategy: Strategy
    ) -> None:
        """Test name existence check."""
        assert not repository.name_exists("New Trade")

        repository.save(sample_strategy, "New Trade")

        assert repository.name_exists("New Trade")
        assert not repository.name_exists("Other Trade")

    def test_update_trade(
        self, repository: TradeRepository, sample_strategy: Strategy
    ) -> None:
        """Test updating an existing trade."""
        trade_id = repository.save(sample_strategy, "Original")

        # Create updated strategy with different spot
        updated_underlier = Underlier(
            symbol="SPY",
            spot=460.0,  # Changed
            multiplier=100,
            currency="USD",
        )
        contract = OptionContract(
            underlier=updated_underlier,
            expiry=date(2024, 3, 15),
            strike=465.0,  # Changed
            type=OptionType.PUT,  # Changed
        )
        leg = OptionLeg(
            contract=contract,
            side=Side.SELL,  # Changed
            quantity=2,  # Changed
            entry_price=6.00,
        )
        updated_strategy = Strategy(
            name="Original",
            underlier=updated_underlier,
            legs=[leg],
        )

        repository.update(trade_id, updated_strategy, "Updated notes")

        result = repository.get_by_id(trade_id)
        assert result is not None

        loaded, notes = result
        assert loaded.underlier.spot == 460.0
        assert loaded.legs[0].contract.strike == 465.0
        assert loaded.legs[0].contract.type == OptionType.PUT
        assert loaded.legs[0].side == Side.SELL
        assert notes == "Updated notes"

    def test_update_nonexistent_raises(
        self, repository: TradeRepository, sample_strategy: Strategy
    ) -> None:
        """Test updating non-existent trade raises error."""
        with pytest.raises(ValueError, match="not found"):
            repository.update(9999, sample_strategy)

    def test_multi_leg_round_trip(
        self, repository: TradeRepository, multi_leg_strategy: Strategy
    ) -> None:
        """Test saving and loading multi-leg strategy."""
        trade_id = repository.save(multi_leg_strategy, "Multi Leg Test")

        result = repository.get_by_id(trade_id)
        assert result is not None

        loaded, _ = result
        assert len(loaded.legs) == 2

        # Verify leg details
        call_leg = next(
            (leg for leg in loaded.legs if leg.contract.type == OptionType.CALL), None
        )
        put_leg = next(
            (leg for leg in loaded.legs if leg.contract.type == OptionType.PUT), None
        )

        assert call_leg is not None
        assert call_leg.contract.strike == 185.0
        assert call_leg.side == Side.BUY
        assert call_leg.quantity == 2

        assert put_leg is not None
        assert put_leg.contract.strike == 175.0
        assert put_leg.side == Side.SELL
        assert put_leg.quantity == 1

    def test_trade_summary_leg_count(
        self, repository: TradeRepository, multi_leg_strategy: Strategy
    ) -> None:
        """Test that trade summary includes correct leg count."""
        repository.save(multi_leg_strategy, "Summary Test")

        trades = repository.list_all()

        assert len(trades) == 1
        assert trades[0].leg_count == 2
        assert trades[0].underlier_symbol == "AAPL"
