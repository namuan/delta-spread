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
