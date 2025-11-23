from datetime import date

from delta_spread.domain.models import (
    OptionContract,
    OptionLeg,
    OptionType,
    Side,
    Strategy,
    Underlier,
)
from delta_spread.services.aggregation import AggregationService
from mocks.pricing_mock import MockPricingService


def test_aggregation_vertical_spread_break_even_and_extremes() -> None:
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
    pricing = MockPricingService()
    agg = AggregationService(pricing)
    ivs = {(6600.0, OptionType.CALL): 0.2, (6700.0, OptionType.CALL): 0.2}
    m = agg.aggregate(s, spot=u.spot, ivs=ivs)
    assert m.net_debit_credit == (10.0 * 100) - (5.0 * 100)
    assert m.max_profit > 0
    assert m.max_loss < 0
    assert len(m.break_evens) >= 1


def test_greeks_sum() -> None:
    u = Underlier(symbol="SPX", spot=6600.0, multiplier=100, currency="USD")
    c1 = OptionContract(
        underlier=u, expiry=date(2025, 12, 15), strike=6600.0, type=OptionType.CALL
    )
    c2 = OptionContract(
        underlier=u, expiry=date(2025, 12, 15), strike=6500.0, type=OptionType.PUT
    )
    l1 = OptionLeg(contract=c1, side=Side.BUY, quantity=2, entry_price=10.0)
    l2 = OptionLeg(contract=c2, side=Side.SELL, quantity=3, entry_price=8.0)
    s = Strategy(name="Mixed", underlier=u, legs=[l1, l2])
    pricing = MockPricingService()
    agg = AggregationService(pricing)
    ivs = {(6600.0, OptionType.CALL): 0.25, (6500.0, OptionType.PUT): 0.18}
    m = agg.aggregate(s, spot=u.spot, ivs=ivs)
    assert m.delta != 0
    assert m.gamma > 0
    assert m.vega > 0
