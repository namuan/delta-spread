from delta_spread.domain.models import AggregationGrid, StrategyMetrics
from delta_spread.services.presenter import MetricsPresenter


def test_metrics_presenter_formats_currency_and_breakevens_range() -> None:
    metrics = StrategyMetrics(
        net_debit_credit=1234.5,
        max_profit=5678.9,
        max_loss=210.0,
        break_evens=[100.0, 110.0],
        delta=0.0,
        gamma=0.0,
        theta=0.0,
        vega=0.0,
        margin_estimate=0.0,
        grid=AggregationGrid(prices=[95.0, 100.0, 105.0], pnls=[-10.0, 0.0, 10.0]),
    )
    pm = MetricsPresenter.prepare(metrics)
    assert pm.net_text == "$1,234.50"
    assert pm.max_profit_text == "$5,678.90"
    assert pm.max_loss_text == "$210.00"
    assert pm.breakevens_text == "Between 100.00 - 110.00"
    assert pm.pop_text == "-"


def test_metrics_presenter_breakevens_single_or_none() -> None:
    m1 = StrategyMetrics(
        net_debit_credit=0.0,
        max_profit=0.0,
        max_loss=0.0,
        break_evens=[101.2345],
        delta=0.0,
        gamma=0.0,
        theta=0.0,
        vega=0.0,
        margin_estimate=0.0,
        grid=AggregationGrid(prices=[], pnls=[]),
    )
    pm1 = MetricsPresenter.prepare(m1)
    assert pm1.breakevens_text == "101.23"
    m2 = StrategyMetrics(
        net_debit_credit=0.0,
        max_profit=0.0,
        max_loss=0.0,
        break_evens=[],
        delta=0.0,
        gamma=0.0,
        theta=0.0,
        vega=0.0,
        margin_estimate=0.0,
        grid=None,
    )
    pm2 = MetricsPresenter.prepare(m2)
    assert pm2.breakevens_text == "-"
