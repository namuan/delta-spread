from typing import Protocol

from ..domain.models import LegMetrics, OptionLeg


class PricingService(Protocol):
    def price_and_greeks(
        self, leg: OptionLeg, spot: float, iv: float
    ) -> LegMetrics: ...
