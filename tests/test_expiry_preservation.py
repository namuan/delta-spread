"""Tests for trade save/load preserving expiry date.

Verifies that saving a trade and loading it back preserves
the original expiry date on the strategy's legs, and that
the controller selects the correct expiry when expiries load.
"""

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
from delta_spread.services.aggregation import AggregationService
from delta_spread.services.async_quote_service import AsyncQuoteService
from delta_spread.services.quote_service import QuoteService
from delta_spread.services.strategy_manager import StrategyManager
from delta_spread.services.trade_service import TradeService
from delta_spread.services.workers.manager import WorkerManager
from delta_spread.ui.controllers.main_window_controller import MainWindowController
from mocks.options_data_mock import MockOptionsDataService
from mocks.pricing_mock import MockPricingService


def _make_strategy(expiry: date, symbol: str = "SPY", spot: float = 500.0) -> Strategy:
    underlier = Underlier(symbol=symbol, spot=spot, multiplier=100, currency="USD")
    contract = OptionContract(
        underlier=underlier,
        expiry=expiry,
        strike=505.0,
        type=OptionType.CALL,
    )
    leg = OptionLeg(
        contract=contract,
        side=Side.BUY,
        quantity=1,
        entry_price=3.50,
    )
    return Strategy(name="Test Trade", underlier=underlier, legs=[leg])


@pytest.fixture
def db_connection() -> DatabaseConnection:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_expiry.db"
        db = DatabaseConnection(db_path)
        db.initialize_schema()
        yield db
        db.close()


@pytest.fixture
def trade_service(db_connection: DatabaseConnection) -> TradeService:
    repo = TradeRepository(db_connection)
    return TradeService(repo)


@pytest.fixture
def controller() -> MainWindowController:
    data_service = MockOptionsDataService()
    pricing = MockPricingService()
    aggregator = AggregationService(pricing)
    quote_service = QuoteService(data_service)
    worker_manager = WorkerManager()
    async_service = AsyncQuoteService(data_service, worker_manager)
    mgr = StrategyManager()
    return MainWindowController(
        strategy_manager=mgr,
        quote_service=quote_service,
        aggregator=aggregator,
        async_quote_service=async_service,
    )


class TestExpiryPersistence:
    def test_save_load_round_trip_preserves_expiry(
        self, trade_service: TradeService
    ) -> None:
        original_expiry = date(2026, 6, 19)
        strategy = _make_strategy(original_expiry)

        trade_id = trade_service.save_trade(strategy, "Expiry Round Trip")
        loaded = trade_service.load_trade(trade_id)

        assert loaded is not None
        assert loaded.legs[0].contract.expiry == original_expiry

    def test_save_load_preserves_non_today_expiry(
        self, trade_service: TradeService
    ) -> None:
        future_expiry = date(2026, 9, 18)
        strategy = _make_strategy(future_expiry)

        trade_id = trade_service.save_trade(strategy, "Future Expiry")
        loaded = trade_service.load_trade(trade_id)

        assert loaded is not None
        assert loaded.legs[0].contract.expiry == future_expiry
        assert loaded.legs[0].contract.expiry != date.today()

    def test_update_preserves_changed_expiry(self, trade_service: TradeService) -> None:
        original_expiry = date(2026, 3, 20)
        strategy = _make_strategy(original_expiry)

        trade_id = trade_service.save_trade(strategy, "Expiry Update")

        updated_expiry = date(2026, 9, 18)
        underlier = strategy.underlier
        new_contract = OptionContract(
            underlier=underlier,
            expiry=updated_expiry,
            strike=510.0,
            type=OptionType.PUT,
        )
        new_leg = OptionLeg(
            contract=new_contract,
            side=Side.SELL,
            quantity=2,
            entry_price=2.00,
        )
        updated = Strategy(
            name="Expiry Update",
            underlier=underlier,
            legs=[new_leg],
        )

        trade_service.update_trade(trade_id, updated)

        loaded = trade_service.load_trade(trade_id)
        assert loaded is not None
        assert loaded.legs[0].contract.expiry == updated_expiry


class TestExpirySelectionAfterLoad:
    def test_on_expiries_loaded_selects_strategy_expiry_not_first(
        self, controller: MainWindowController
    ) -> None:
        future_expiry = date(2026, 9, 18)
        strategy = _make_strategy(future_expiry)
        controller.strategy_manager.strategy = strategy

        first_expiry = date(2026, 5, 16)
        expiries = [first_expiry, date(2026, 6, 19), future_expiry, date(2026, 12, 18)]

        controller._on_expiries_loaded(expiries)

        assert controller.selected_expiry == future_expiry
        assert controller.selected_expiry != first_expiry

    def test_on_expiries_loaded_preserves_strategy_expiry_on_load(
        self, controller: MainWindowController
    ) -> None:
        saved_expiry = date(2026, 6, 19)
        strategy = _make_strategy(saved_expiry)
        controller.strategy_manager.strategy = strategy

        expiries = [date(2026, 5, 16), saved_expiry, date(2026, 9, 18)]

        controller._on_expiries_loaded(expiries)

        assert controller.strategy_manager.strategy is not None
        assert (
            controller.strategy_manager.strategy.legs[0].contract.expiry == saved_expiry
        )
        assert controller.selected_expiry == saved_expiry

    def test_on_expiries_loaded_falls_back_to_first_without_strategy(
        self, controller: MainWindowController
    ) -> None:
        controller._on_expiries_loaded([date(2026, 5, 16), date(2026, 6, 19)])

        assert controller.selected_expiry == date(2026, 5, 16)

    def test_on_expiries_loaded_falls_back_when_strategy_expiry_unavailable(
        self, controller: MainWindowController
    ) -> None:
        old_expiry = date(2025, 1, 17)
        strategy = _make_strategy(old_expiry)
        controller.strategy_manager.strategy = strategy

        available = [date(2026, 5, 16), date(2026, 6, 19)]

        controller._on_expiries_loaded(available)

        assert controller.selected_expiry == date(2026, 5, 16)

    def test_on_expiries_loaded_does_not_modify_strategy_expiry(
        self, controller: MainWindowController
    ) -> None:
        saved_expiry = date(2026, 9, 18)
        strategy = _make_strategy(saved_expiry)
        controller.strategy_manager.strategy = strategy

        first_expiry = date(2026, 5, 16)
        expiries = [first_expiry, date(2026, 6, 19), saved_expiry]

        controller.expiries = []
        controller.selected_expiry = None
        controller._on_expiries_loaded(expiries)

        assert controller.strategy_manager.strategy is not None
        assert (
            controller.strategy_manager.strategy.legs[0].contract.expiry == saved_expiry
        )
