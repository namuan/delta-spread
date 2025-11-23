from datetime import date

from delta_spread.domain.models import (
    OptionContract,
    OptionLeg,
    OptionType,
    Side,
    Underlier,
)
from mocks.pricing_mock import MockPricingService


def test_mock_pricing_service_returns_metrics() -> None:
    u = Underlier(symbol="SPX", spot=6600.0, multiplier=100, currency="USD")
    c = OptionContract(
        underlier=u, expiry=date(2025, 12, 15), strike=6600.0, type=OptionType.CALL
    )
    leg = OptionLeg(contract=c, side=Side.BUY, quantity=1, entry_price=10.0)
    svc = MockPricingService()
    metrics = svc.price_and_greeks(leg, spot=u.spot, iv=0.2)
    assert metrics.price > 0
    assert -1.0 <= metrics.delta <= 1.0
    assert metrics.gamma >= 0
    assert metrics.vega >= 0
