from delta_spread.domain.models import AggregationGrid, StrategyMetrics
from delta_spread.services.presenter import ChartPresenter


def test_chart_presenter_with_grid() -> None:
    grid = AggregationGrid(prices=[100.0, 105.0, 110.0], pnls=[-10.0, 0.0, 15.0])
    metrics = StrategyMetrics(
        net_debit_credit=5.0,
        max_profit=20.0,
        max_loss=15.0,
        break_evens=[104.0, 107.0],
        delta=0.3,
        gamma=0.01,
        theta=-0.02,
        vega=0.1,
        margin_estimate=1000.0,
        grid=grid,
    )
    cd = ChartPresenter.prepare(
        metrics, strike_lines=[100.0, 110.0], current_price=105.0
    )
    # ChartPresenter adds 2% padding to x-axis
    expected_padding = 0.02 * (110.0 - 100.0)  # 0.2
    assert cd.x_min == 100.0 - expected_padding and cd.x_max == 110.0 + expected_padding
    assert cd.y_min == -10.0 and cd.y_max == 15.0
    assert cd.prices == grid.prices and cd.pnls == grid.pnls
    assert cd.strike_lines == [100.0, 110.0]
    assert cd.current_price == 105.0


def test_chart_presenter_empty_grid_defaults() -> None:
    metrics = StrategyMetrics(
        net_debit_credit=0.0,
        max_profit=0.0,
        max_loss=0.0,
        break_evens=[],
        delta=0.0,
        gamma=0.0,
        theta=0.0,
        vega=0.0,
        margin_estimate=0.0,
        grid=AggregationGrid(prices=[], pnls=[]),
    )
    cd = ChartPresenter.prepare(metrics, strike_lines=[101.0], current_price=100.0)
    assert cd.prices == [] and cd.pnls == []
    assert cd.x_min == 0.0 and cd.x_max == 1.0
    assert cd.y_min == -1.0 and cd.y_max == 1.0
    assert cd.strike_lines == [101.0]
