from datetime import date, datetime

from pydantic import ValidationError
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


def test_option_quote_validation() -> None:
    q = OptionQuote(bid=1.0, ask=2.0, mid=1.5, iv=0.2, last_updated=datetime.now())
    assert q.bid <= q.mid <= q.ask
    with pytest.raises(ValidationError):
        OptionQuote(bid=2.0, ask=1.0, mid=1.5, iv=0.2, last_updated=datetime.now())
    with pytest.raises(ValidationError):
        OptionQuote(bid=1.0, ask=2.0, mid=3.0, iv=-0.1, last_updated=datetime.now())


def test_strategy_same_expiry_enforced() -> None:
    u = Underlier(symbol="SPX", spot=6600.0, multiplier=100, currency="USD")
    c1 = OptionContract(
        underlier=u, expiry=date(2025, 12, 15), strike=6600.0, type=OptionType.CALL
    )
    c2 = OptionContract(
        underlier=u, expiry=date(2025, 12, 22), strike=6700.0, type=OptionType.CALL
    )
    l1 = OptionLeg(contract=c1, side=Side.BUY, quantity=1, entry_price=10.0)
    l2 = OptionLeg(contract=c2, side=Side.SELL, quantity=1, entry_price=5.0)
    with pytest.raises(ValidationError):
        Strategy(name="Vertical", underlier=u, legs=[l1, l2])


def test_strategy_all_legs_share_underlier() -> None:
    u1 = Underlier(symbol="SPX", spot=6600.0, multiplier=100, currency="USD")
    u2 = Underlier(symbol="QQQ", spot=490.0, multiplier=100, currency="USD")
    c1 = OptionContract(
        underlier=u1, expiry=date(2025, 12, 15), strike=6600.0, type=OptionType.CALL
    )
    c2 = OptionContract(
        underlier=u2, expiry=date(2025, 12, 15), strike=6700.0, type=OptionType.CALL
    )
    l1 = OptionLeg(contract=c1, side=Side.BUY, quantity=1, entry_price=10.0)
    l2 = OptionLeg(contract=c2, side=Side.SELL, quantity=1, entry_price=5.0)
    with pytest.raises(ValidationError):
        Strategy(name="Invalid", underlier=u1, legs=[l1, l2])


def test_strategy_valid_vertical() -> None:
    u = Underlier(symbol="SPX", spot=6600.0, multiplier=100, currency="USD")
    c1 = OptionContract(
        underlier=u, expiry=date(2025, 12, 15), strike=6600.0, type=OptionType.CALL
    )
    c2 = OptionContract(
        underlier=u, expiry=date(2025, 12, 15), strike=6700.0, type=OptionType.CALL
    )
    l1 = OptionLeg(contract=c1, side=Side.BUY, quantity=1, entry_price=10.0)
    l2 = OptionLeg(contract=c2, side=Side.SELL, quantity=1, entry_price=5.0)
    s = Strategy(name="Vertical", underlier=u, legs=[l1, l2])
    assert s.underlier.symbol == "SPX"
