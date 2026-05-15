"""Tests for batch expiry update flow in the controller.

Verifies that changing expiry on a multi-leg strategy collects
all async quotes before performing a single atomic update,
avoiding the intermediate same_expiry validation error.
"""

from __future__ import annotations

from datetime import date, datetime
from unittest.mock import patch

import pytest

from delta_spread.domain.models import (
    OptionContract,
    OptionLeg,
    OptionQuote,
    OptionType,
    Side,
    Strategy,
    Underlier,
)
from delta_spread.services.aggregation import AggregationService
from delta_spread.services.async_quote_service import AsyncQuoteService
from delta_spread.services.quote_service import QuoteService
from delta_spread.services.strategy_manager import StrategyManager
from delta_spread.services.workers.manager import WorkerManager
from delta_spread.ui.controllers.main_window_controller import (
    MainWindowController,
    PendingExpiryChange,
)
from mocks.options_data_mock import MockOptionsDataService
from mocks.pricing_mock import MockPricingService


def _underlier(symbol: str = "SPY", spot: float = 500.0) -> Underlier:
    return Underlier(symbol=symbol, spot=spot, multiplier=100, currency="USD")


def _make_two_leg_strategy(
    expiry: date = date(2026, 1, 17),
) -> Strategy:
    u = _underlier()
    leg1 = OptionLeg(
        contract=OptionContract(
            underlier=u, expiry=expiry, strike=500.0, type=OptionType.CALL
        ),
        side=Side.BUY,
        quantity=1,
        entry_price=3.50,
    )
    leg2 = OptionLeg(
        contract=OptionContract(
            underlier=u, expiry=expiry, strike=510.0, type=OptionType.PUT
        ),
        side=Side.SELL,
        quantity=1,
        entry_price=2.00,
    )
    return Strategy(name="Spread", underlier=u, legs=[leg1, leg2])


def _make_quote(mid: float = 3.00) -> OptionQuote:
    return OptionQuote(
        bid=mid - 0.10,
        ask=mid + 0.10,
        mid=mid,
        iv=0.25,
        last_updated=datetime.now(),
    )


class FakeInstrumentPanel:
    def get_symbol(self) -> str:
        return "SPY"


class FakeMetricsPanel:
    def update_metrics(self, *args: object) -> None:
        pass

    def update_greeks(self, *args: object) -> None:
        pass


class FakeChartWidget:
    def set_chart_data(self, *args: object) -> None:
        pass

    def repaint(self) -> None:
        pass


@pytest.fixture
def controller() -> MainWindowController:
    data_service = MockOptionsDataService()
    pricing = MockPricingService()
    aggregator = AggregationService(pricing)
    quote_service = QuoteService(data_service)
    worker_manager = WorkerManager()
    async_service = AsyncQuoteService(data_service, worker_manager)
    mgr = StrategyManager()
    ctrl = MainWindowController(
        strategy_manager=mgr,
        quote_service=quote_service,
        aggregator=aggregator,
        async_quote_service=async_service,
    )
    ctrl.instrument_panel = FakeInstrumentPanel()  # type: ignore[arg-type]
    ctrl.metrics_panel = FakeMetricsPanel()  # type: ignore[arg-type]
    ctrl.chart = FakeChartWidget()  # type: ignore[arg-type]
    return ctrl


class TestPendingExpiryChangeDataclass:
    def test_fields(self) -> None:
        p = PendingExpiryChange(
            leg_idx=0,
            new_expiry=date(2026, 2, 21),
            strike=500.0,
            option_type=OptionType.CALL,
        )
        assert p.leg_idx == 0
        assert p.new_expiry == date(2026, 2, 21)
        assert p.strike == 500.0
        assert p.option_type is OptionType.CALL


class TestBatchExpiryUpdateFlow:
    def test_pending_changes_populated_for_all_legs(
        self, controller: MainWindowController
    ) -> None:
        strategy = _make_two_leg_strategy()
        controller.strategy_manager.strategy = strategy
        new_expiry = date(2026, 2, 21)

        with patch.object(controller.async_quote_service, "fetch_quote"):
            controller._update_strategy_legs_expiry(new_expiry)

        assert len(controller._pending_expiry_changes) == 2
        assert controller._pending_expiry_target == new_expiry
        assert controller._pending_expiry_changes[0].leg_idx == 0
        assert controller._pending_expiry_changes[1].leg_idx == 1

    def test_pending_changes_cleared_before_new_batch(
        self, controller: MainWindowController
    ) -> None:
        strategy = _make_two_leg_strategy()
        controller.strategy_manager.strategy = strategy

        controller._pending_expiry_changes = [
            PendingExpiryChange(
                leg_idx=99,
                new_expiry=date(2025, 1, 1),
                strike=1.0,
                option_type=OptionType.CALL,
            )
        ]
        controller._pending_expiry_prices = {99: 1.0}

        new_expiry = date(2026, 3, 20)
        with patch.object(controller.async_quote_service, "fetch_quote"):
            controller._update_strategy_legs_expiry(new_expiry)

        assert len(controller._pending_expiry_changes) == 2
        assert 99 not in controller._pending_expiry_prices
        assert controller._pending_expiry_target == new_expiry

    def test_collects_prices_and_completes_batch(
        self, controller: MainWindowController
    ) -> None:
        strategy = _make_two_leg_strategy()
        controller.strategy_manager.strategy = strategy

        new_expiry = date(2026, 2, 21)
        controller._pending_expiry_target = new_expiry
        controller._pending_expiry_changes = [
            PendingExpiryChange(
                leg_idx=0,
                new_expiry=new_expiry,
                strike=500.0,
                option_type=OptionType.CALL,
            ),
            PendingExpiryChange(
                leg_idx=1,
                new_expiry=new_expiry,
                strike=510.0,
                option_type=OptionType.PUT,
            ),
        ]
        controller._pending_expiry_prices = {}

        leg0 = strategy.legs[0]
        quote0 = _make_quote(mid=4.50)
        result = controller._complete_pending_expiry_change(
            new_expiry, leg0.contract.strike, leg0.contract.type, quote0
        )
        assert result is True
        assert controller._pending_expiry_target is not None
        assert controller._pending_expiry_prices[0] == 4.50

        leg1 = strategy.legs[1]
        quote1 = _make_quote(mid=2.30)
        result2 = controller._complete_pending_expiry_change(
            new_expiry, leg1.contract.strike, leg1.contract.type, quote1
        )
        assert result2 is True

        updated = controller.strategy_manager.strategy
        assert updated is not None
        assert updated.legs[0].contract.expiry == new_expiry
        assert updated.legs[1].contract.expiry == new_expiry
        assert updated.legs[0].entry_price == 4.50
        assert updated.legs[1].entry_price == 2.30

        assert controller._pending_expiry_prices == {}
        assert controller._pending_expiry_target is None

    def test_no_strategy_update_until_all_quotes_arrive(
        self, controller: MainWindowController
    ) -> None:
        strategy = _make_two_leg_strategy()
        controller.strategy_manager.strategy = strategy

        original_expiry = strategy.legs[0].contract.expiry
        new_expiry = date(2026, 2, 21)
        controller._pending_expiry_target = new_expiry
        controller._pending_expiry_changes = [
            PendingExpiryChange(
                leg_idx=0,
                new_expiry=new_expiry,
                strike=500.0,
                option_type=OptionType.CALL,
            ),
            PendingExpiryChange(
                leg_idx=1,
                new_expiry=new_expiry,
                strike=510.0,
                option_type=OptionType.PUT,
            ),
        ]
        controller._pending_expiry_prices = {}

        quote0 = _make_quote(mid=4.50)
        leg0 = strategy.legs[0]
        controller._complete_pending_expiry_change(
            new_expiry, leg0.contract.strike, leg0.contract.type, quote0
        )

        current = controller.strategy_manager.strategy
        assert current is not None
        assert current.legs[0].contract.expiry == original_expiry
        assert current.legs[1].contract.expiry == original_expiry

    def test_returns_false_when_no_matching_pending(
        self, controller: MainWindowController
    ) -> None:
        result = controller._complete_pending_expiry_change(
            date(2026, 2, 21), 500.0, OptionType.CALL, _make_quote()
        )
        assert result is False

    def test_same_expiry_skips_unchanged(
        self, controller: MainWindowController
    ) -> None:
        strategy = _make_two_leg_strategy(expiry=date(2026, 1, 17))
        controller.strategy_manager.strategy = strategy

        with patch.object(controller.async_quote_service, "fetch_quote"):
            controller._update_strategy_legs_expiry(date(2026, 1, 17))

        assert len(controller._pending_expiry_changes) == 0
        assert controller._pending_expiry_target is None

    def test_three_leg_strategy_batch_update(
        self, controller: MainWindowController
    ) -> None:
        u = _underlier()
        expiry = date(2026, 1, 17)
        leg1 = OptionLeg(
            contract=OptionContract(
                underlier=u, expiry=expiry, strike=500.0, type=OptionType.CALL
            ),
            side=Side.BUY,
            quantity=1,
            entry_price=3.50,
        )
        leg2 = OptionLeg(
            contract=OptionContract(
                underlier=u, expiry=expiry, strike=510.0, type=OptionType.PUT
            ),
            side=Side.SELL,
            quantity=1,
            entry_price=2.00,
        )
        leg3 = OptionLeg(
            contract=OptionContract(
                underlier=u, expiry=expiry, strike=490.0, type=OptionType.CALL
            ),
            side=Side.BUY,
            quantity=1,
            entry_price=5.00,
        )
        strategy = Strategy(name="ThreeLeg", underlier=u, legs=[leg1, leg2, leg3])
        controller.strategy_manager.strategy = strategy

        new_expiry = date(2026, 3, 20)
        controller._pending_expiry_target = new_expiry
        controller._pending_expiry_changes = [
            PendingExpiryChange(
                leg_idx=0,
                new_expiry=new_expiry,
                strike=500.0,
                option_type=OptionType.CALL,
            ),
            PendingExpiryChange(
                leg_idx=1,
                new_expiry=new_expiry,
                strike=510.0,
                option_type=OptionType.PUT,
            ),
            PendingExpiryChange(
                leg_idx=2,
                new_expiry=new_expiry,
                strike=490.0,
                option_type=OptionType.CALL,
            ),
        ]
        controller._pending_expiry_prices = {}

        quotes = {
            (500.0, OptionType.CALL): _make_quote(mid=4.10),
            (510.0, OptionType.PUT): _make_quote(mid=1.90),
            (490.0, OptionType.CALL): _make_quote(mid=5.50),
        }

        for pending in list(controller._pending_expiry_changes):
            q = quotes[pending.strike, pending.option_type]
            controller._complete_pending_expiry_change(
                new_expiry, pending.strike, pending.option_type, q
            )

        updated = controller.strategy_manager.strategy
        assert updated is not None
        for leg in updated.legs:
            assert leg.contract.expiry == new_expiry
        assert updated.legs[0].entry_price == 4.10
        assert updated.legs[1].entry_price == 1.90
        assert updated.legs[2].entry_price == 5.50
