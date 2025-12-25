from collections.abc import Mapping

from ..domain.models import AggregationGrid, OptionType, Side, Strategy, StrategyMetrics
from .pricing import PricingService


class AggregationService:
    def __init__(self, pricing: PricingService) -> None:
        super().__init__()
        self._pricing = pricing

    @property
    def pricing_service(self) -> PricingService:
        """Get the pricing service."""
        return self._pricing

    def aggregate(
        self,
        strategy: Strategy,
        spot: float,
        ivs: Mapping[tuple[float, OptionType], float],
    ) -> StrategyMetrics:
        multiplier = strategy.underlier.multiplier
        net = self._compute_net(strategy)
        prices = self._build_price_grid(strategy)
        pnls = self._compute_pnl_curve(strategy, prices, multiplier)
        bevs = self._find_break_evens(prices, pnls)
        delta, gamma, theta, vega = self._sum_greeks(strategy, spot, ivs)
        grid = AggregationGrid(prices=prices, pnls=pnls)
        return StrategyMetrics(
            net_debit_credit=net,
            max_profit=max(pnls),
            max_loss=min(pnls),
            break_evens=bevs,
            delta=delta,
            gamma=gamma,
            theta=theta,
            vega=vega,
            margin_estimate=0.0,
            grid=grid,
        )

    @staticmethod
    def _compute_net(strategy: Strategy) -> float:
        multiplier = strategy.underlier.multiplier
        net = 0.0
        for leg in strategy.legs:
            sign = 1.0 if leg.side is Side.BUY else -1.0
            price = leg.entry_price or 0.0
            net += sign * price * leg.quantity * multiplier
        return net

    @staticmethod
    def _build_price_grid(strategy: Strategy) -> list[float]:
        strikes = [leg.contract.strike for leg in strategy.legs]
        mn = min(strikes)
        mx = max(strikes)
        span = max(50.0, (mx - mn) * 2.0)
        start = mn - 0.2 * span
        end = mx + 0.2 * span
        steps = 200
        return [start + (i * (end - start) / steps) for i in range(steps + 1)]

    @staticmethod
    def _compute_pnl_curve(
        strategy: Strategy, prices: list[float], multiplier: int
    ) -> list[float]:
        pnls: list[float] = []
        for s in prices:
            pnl = 0.0
            for leg in strategy.legs:
                qty = float(leg.quantity)
                sign = 1.0 if leg.side is Side.BUY else -1.0
                if leg.contract.type is OptionType.CALL:
                    payoff = max(s - leg.contract.strike, 0.0) * multiplier
                else:
                    payoff = max(leg.contract.strike - s, 0.0) * multiplier
                entry = (leg.entry_price or 0.0) * multiplier
                pnl += qty * (sign * payoff - sign * entry)
            pnls.append(pnl)
        return pnls

    @staticmethod
    def _find_break_evens(prices: list[float], pnls: list[float]) -> list[float]:
        bevs: list[float] = []
        for i in range(1, len(prices)):
            a = pnls[i - 1]
            b = pnls[i]
            if a == 0 or b == 0:
                x = prices[i] if b == 0 else prices[i - 1]
                if x not in bevs:
                    bevs.append(x)
                continue
            if (a < 0 and b > 0) or (a > 0 and b < 0):
                pa = a
                pb = b
                xa = prices[i - 1]
                xb = prices[i]
                x = xb if pb - pa == 0 else xa + (0 - pa) * (xb - xa) / (pb - pa)
                bevs.append(x)
        return bevs

    def _sum_greeks(
        self,
        strategy: Strategy,
        spot: float,
        ivs: Mapping[tuple[float, OptionType], float],
    ) -> tuple[float, float, float, float]:
        delta = 0.0
        gamma = 0.0
        theta = 0.0
        vega = 0.0
        for leg in strategy.legs:
            iv = ivs.get((leg.contract.strike, leg.contract.type), 0.2)
            m = self._pricing.price_and_greeks(leg, spot, iv)
            delta += m.delta * leg.quantity
            gamma += m.gamma * leg.quantity
            theta += m.theta * leg.quantity
            vega += m.vega * leg.quantity
        return delta, gamma, theta, vega
