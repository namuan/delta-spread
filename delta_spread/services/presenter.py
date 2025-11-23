from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..domain.models import StrategyMetrics

if TYPE_CHECKING:
    from ..domain.models import AggregationGrid


@dataclass(frozen=True)
class ChartData:
    prices: list[float]
    pnls: list[float]
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    strike_lines: list[float]
    current_price: float


class ChartPresenter:
    @staticmethod
    def prepare(
        metrics: StrategyMetrics, strike_lines: Iterable[float], current_price: float
    ) -> ChartData:
        grid: AggregationGrid | None = metrics.grid
        if grid is None or not grid.prices:
            return ChartData(
                prices=[],
                pnls=[],
                x_min=0.0,
                x_max=1.0,
                y_min=-1.0,
                y_max=1.0,
                strike_lines=list(strike_lines),
                current_price=current_price,
            )
        x_min = min(grid.prices)
        x_max = max(grid.prices)
        y_min = min(grid.pnls)
        y_max = max(grid.pnls)
        return ChartData(
            prices=grid.prices,
            pnls=grid.pnls,
            x_min=x_min,
            x_max=x_max,
            y_min=y_min,
            y_max=y_max,
            strike_lines=list(strike_lines),
            current_price=current_price,
        )


@dataclass(frozen=True)
class PanelMetrics:
    net_text: str
    max_loss_text: str
    max_profit_text: str
    breakevens_text: str
    pop_text: str


class MetricsPresenter:
    @staticmethod
    def prepare(metrics: StrategyMetrics) -> PanelMetrics:
        net = f"${metrics.net_debit_credit:,.2f}"
        max_loss = f"${metrics.max_loss:,.2f}"
        max_profit = f"${metrics.max_profit:,.2f}"
        if not metrics.break_evens:
            be_text = "-"
        elif len(metrics.break_evens) == 1:
            be_text = f"{metrics.break_evens[0]:,.2f}"
        else:
            lo = min(metrics.break_evens)
            hi = max(metrics.break_evens)
            be_text = f"Between {lo:,.2f} - {hi:,.2f}"
        pop = "-"
        return PanelMetrics(
            net_text=net,
            max_loss_text=max_loss,
            max_profit_text=max_profit,
            breakevens_text=be_text,
            pop_text=pop,
        )
