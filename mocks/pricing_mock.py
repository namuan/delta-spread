from math import tanh

from delta_spread.domain.models import LegMetrics, OptionLeg, OptionType, Side


class MockPricingService:
    def __init__(
        self, vega_coef: float = 0.1, gamma_coef: float = 0.02, theta_coef: float = 0.01
    ) -> None:
        super().__init__()
        self._vega_coef = vega_coef
        self._gamma_coef = gamma_coef
        self._theta_coef = theta_coef

    def price_and_greeks(self, leg: OptionLeg, spot: float, iv: float) -> LegMetrics:
        m = spot - leg.contract.strike
        base = iv * leg.contract.strike * 0.001
        price = max(0.01, base + abs(m) * 0.002)
        sgn = 1 if leg.side is Side.BUY else -1
        call_dir = 1 if leg.contract.type is OptionType.CALL else -1
        delta_mag = 0.5 + 0.4 * tanh(m / max(1.0, leg.contract.strike * 0.05))
        delta = sgn * call_dir * delta_mag
        gamma = self._gamma_coef * iv
        theta = -sgn * self._theta_coef * iv
        vega = self._vega_coef * iv
        return LegMetrics(price=price, delta=delta, gamma=gamma, theta=theta, vega=vega)
