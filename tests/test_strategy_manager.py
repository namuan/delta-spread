from datetime import date

import pytest

from delta_spread.domain.models import (
    OptionContract,
    OptionLeg,
    OptionType,
    Side,
    Strategy,
    StrategyConstraints,
    Underlier,
)
from delta_spread.services.strategy_manager import StrategyManager


def _underlier(symbol: str = "SPY") -> Underlier:
    return Underlier(symbol=symbol, spot=500.0, multiplier=100, currency="USD")


def _leg(
    *,
    underlier: Underlier,
    expiry: date,
    strike: float,
    option_type: OptionType,
    side: Side,
    quantity: int = 1,
    entry_price: float = 1.0,
) -> OptionLeg:
    contract = OptionContract(
        underlier=underlier,
        expiry=expiry,
        strike=strike,
        type=option_type,
    )
    return OptionLeg(
        contract=contract,
        side=side,
        quantity=quantity,
        entry_price=entry_price,
    )


def test_strategy_manager_empty_state() -> None:
    mgr = StrategyManager()
    assert mgr.has_strategy() is False
    assert mgr.strategy is None
    assert mgr.get_underlier() is None
    assert mgr.get_legs() == []


def test_strategy_manager_create_add_remove_and_reset() -> None:
    expiry = date(2026, 1, 17)
    u = _underlier("SPY")
    leg1 = _leg(
        underlier=u,
        expiry=expiry,
        strike=500.0,
        option_type=OptionType.CALL,
        side=Side.BUY,
        entry_price=2.0,
    )

    mgr = StrategyManager()

    with pytest.raises(ValueError, match="no strategy exists"):
        mgr.add_leg(leg1)

    strategy = mgr.create_strategy("Test", u, leg1)
    assert mgr.strategy == strategy
    assert mgr.has_strategy() is True
    assert mgr.get_underlier() == u
    assert mgr.get_legs() == [leg1]

    leg2 = _leg(
        underlier=u,
        expiry=expiry,
        strike=510.0,
        option_type=OptionType.CALL,
        side=Side.SELL,
        entry_price=1.0,
    )

    updated = mgr.add_leg(leg2)
    assert updated is not strategy
    assert len(updated.legs) == 2

    with pytest.raises(ValueError, match="Invalid leg index"):
        mgr.remove_leg(99)

    remaining = mgr.remove_leg(0)
    assert remaining is not None
    assert len(remaining.legs) == 1

    cleared = mgr.remove_leg(0)
    assert cleared is None
    assert mgr.strategy is None

    mgr.strategy = Strategy(name="Temp", underlier=u, legs=[leg1])
    mgr.reset()
    assert mgr.strategy is None


def test_strategy_manager_update_leg_and_preview() -> None:
    expiry = date(2026, 1, 17)
    u = _underlier("SPY")
    base_leg = _leg(
        underlier=u,
        expiry=expiry,
        strike=500.0,
        option_type=OptionType.CALL,
        side=Side.BUY,
        entry_price=2.0,
    )
    mgr = StrategyManager(Strategy(name="Base", underlier=u, legs=[base_leg]))

    with pytest.raises(ValueError, match="Invalid leg index"):
        mgr.update_leg_strike(3, 510.0, 2.0)

    with pytest.raises(ValueError, match="Invalid leg index"):
        mgr.update_leg_type(-1, OptionType.PUT, 1.5)

    updated_type = mgr.update_leg_type(0, OptionType.PUT, 1.5)
    assert updated_type.legs[0].contract.type is OptionType.PUT
    assert updated_type.legs[0].entry_price == 1.5

    updated_strike = mgr.update_leg_strike(0, 520.0, 3.0)
    assert updated_strike.legs[0].contract.strike == 520.0
    assert updated_strike.legs[0].entry_price == 3.0

    preview = mgr.create_preview_strategy(0, 530.0, 4.0)
    assert preview is not None
    assert preview.legs[0].contract.strike == 530.0
    assert preview.legs[0].entry_price == 4.0
    assert mgr.strategy is not None
    assert mgr.strategy.legs[0].contract.strike == 520.0

    assert mgr.create_preview_strategy(99, 530.0, 4.0) is None


def test_get_expiry_for_new_leg_respects_constraints() -> None:
    expiry1 = date(2026, 1, 17)
    expiry2 = date(2026, 2, 21)
    u = _underlier("SPY")

    leg1 = _leg(
        underlier=u,
        expiry=expiry1,
        strike=500.0,
        option_type=OptionType.CALL,
        side=Side.BUY,
    )

    mgr = StrategyManager(
        Strategy(
            name="Constrained",
            underlier=u,
            legs=[leg1],
            constraints=StrategyConstraints(same_expiry=True),
        )
    )

    assert mgr.get_expiry_for_new_leg(expiry2) == expiry1

    mgr.strategy = Strategy(
        name="Unconstrained",
        underlier=u,
        legs=[leg1],
        constraints=StrategyConstraints(same_expiry=False),
    )
    assert mgr.get_expiry_for_new_leg(expiry2) == expiry2
    assert mgr.get_expiry_for_new_leg(None) is None


def test_strategy_manager_update_leg_expiry() -> None:
    """Test updating leg expiry date."""
    expiry1 = date(2026, 1, 17)
    expiry2 = date(2026, 2, 21)
    u = _underlier("SPY")
    base_leg = _leg(
        underlier=u,
        expiry=expiry1,
        strike=500.0,
        option_type=OptionType.CALL,
        side=Side.BUY,
        entry_price=2.0,
    )
    mgr = StrategyManager(Strategy(name="Base", underlier=u, legs=[base_leg]))

    # Test invalid leg index
    with pytest.raises(ValueError, match="Invalid leg index"):
        mgr.update_leg_expiry(3, expiry2, 2.5)

    with pytest.raises(ValueError, match="Invalid leg index"):
        mgr.update_leg_expiry(-1, expiry2, 2.5)

    # Test successful update
    updated = mgr.update_leg_expiry(0, expiry2, 3.0)
    assert updated.legs[0].contract.expiry == expiry2
    assert updated.legs[0].entry_price == 3.0
    # Ensure other fields are preserved
    assert updated.legs[0].contract.strike == 500.0
    assert updated.legs[0].contract.type is OptionType.CALL
    assert updated.legs[0].side is Side.BUY


def test_strategy_manager_update_leg_expiry_no_strategy() -> None:
    """Test that updating expiry fails when no strategy exists."""
    mgr = StrategyManager()

    with pytest.raises(ValueError, match="no strategy exists"):
        mgr.update_leg_expiry(0, date(2026, 2, 21), 2.5)


class TestUpdateAllLegsExpiry:
    """Tests for StrategyManager.update_all_legs_expiry."""

    def _two_leg_strategy(self) -> Strategy:
        u = _underlier("SPY")
        expiry = date(2026, 1, 17)
        leg1 = _leg(
            underlier=u,
            expiry=expiry,
            strike=500.0,
            option_type=OptionType.CALL,
            side=Side.BUY,
            entry_price=3.50,
        )
        leg2 = _leg(
            underlier=u,
            expiry=expiry,
            strike=510.0,
            option_type=OptionType.PUT,
            side=Side.SELL,
            entry_price=2.00,
        )
        return Strategy(name="TwoLeg", underlier=u, legs=[leg1, leg2])

    def test_updates_all_legs_expiry_atomically(self) -> None:
        mgr = StrategyManager(self._two_leg_strategy())
        new_expiry = date(2026, 2, 21)
        entry_prices = {0: 4.10, 1: 1.80}

        result = mgr.update_all_legs_expiry(new_expiry, entry_prices)

        assert result.legs[0].contract.expiry == new_expiry
        assert result.legs[1].contract.expiry == new_expiry
        assert result.legs[0].entry_price == 4.10
        assert result.legs[1].entry_price == 1.80

    def test_preserves_existing_price_for_unspecified_legs(self) -> None:
        mgr = StrategyManager(self._two_leg_strategy())
        new_expiry = date(2026, 3, 20)
        entry_prices = {0: 5.00}

        result = mgr.update_all_legs_expiry(new_expiry, entry_prices)

        assert result.legs[0].contract.expiry == new_expiry
        assert result.legs[1].contract.expiry == new_expiry
        assert result.legs[0].entry_price == 5.00
        assert result.legs[1].entry_price == 2.00

    def test_preserves_strike_type_and_side(self) -> None:
        mgr = StrategyManager(self._two_leg_strategy())
        new_expiry = date(2026, 4, 17)
        entry_prices = {0: 3.00, 1: 2.50}

        result = mgr.update_all_legs_expiry(new_expiry, entry_prices)

        assert result.legs[0].contract.strike == 500.0
        assert result.legs[0].contract.type is OptionType.CALL
        assert result.legs[0].side is Side.BUY
        assert result.legs[1].contract.strike == 510.0
        assert result.legs[1].contract.type is OptionType.PUT
        assert result.legs[1].side is Side.SELL

    def test_same_expiry_validator_passes_after_batch_update(self) -> None:
        mgr = StrategyManager(self._two_leg_strategy())
        new_expiry = date(2026, 5, 15)
        entry_prices = {0: 2.00, 1: 1.50}

        result = mgr.update_all_legs_expiry(new_expiry, entry_prices)

        assert all(leg.contract.expiry == new_expiry for leg in result.legs)

    def test_raises_when_no_strategy(self) -> None:
        mgr = StrategyManager()
        with pytest.raises(ValueError, match="no strategy exists"):
            mgr.update_all_legs_expiry(date(2026, 2, 21), {})

    def test_empty_entry_prices_keeps_all_original_prices(self) -> None:
        mgr = StrategyManager(self._two_leg_strategy())
        new_expiry = date(2026, 6, 19)

        result = mgr.update_all_legs_expiry(new_expiry, {})

        assert result.legs[0].entry_price == 3.50
        assert result.legs[1].entry_price == 2.00
        assert all(leg.contract.expiry == new_expiry for leg in result.legs)

    def test_single_leg_strategy(self) -> None:
        u = _underlier("SPY")
        expiry = date(2026, 1, 17)
        leg = _leg(
            underlier=u,
            expiry=expiry,
            strike=500.0,
            option_type=OptionType.CALL,
            side=Side.BUY,
            entry_price=3.50,
        )
        mgr = StrategyManager(Strategy(name="Single", underlier=u, legs=[leg]))
        new_expiry = date(2026, 2, 21)

        result = mgr.update_all_legs_expiry(new_expiry, {0: 4.00})

        assert result.legs[0].contract.expiry == new_expiry
        assert result.legs[0].entry_price == 4.00
