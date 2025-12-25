"""Main window controller.

This module provides a controller that coordinates between
UI panels and services, handling complex workflows and
state transitions.
"""

from __future__ import annotations

from datetime import date
import logging
from typing import TYPE_CHECKING, cast

from ...domain.models import (
    OptionContract,
    OptionLeg,
    OptionType,
    Side,
    Underlier,
)
from ...services.presenter import ChartData, ChartPresenter, MetricsPresenter
from ..styles import COLOR_DANGER_RED, COLOR_SUCCESS_GREEN

if TYPE_CHECKING:
    from ...domain.models import StrategyMetrics
    from ...services.aggregation import AggregationService
    from ...services.quote_service import QuoteService
    from ...services.strategy_manager import StrategyManager
    from ..chart_widget import ChartWidget
    from ..panels.instrument_info_panel import InstrumentInfoPanel
    from ..panels.metrics_panel import MetricsPanel
    from ..panels.strikes_panel import StrikesPanel
    from ..strike_ruler import BadgeSpec
    from ..timeline_widget import TimelineWidget


class MainWindowController:
    """Controller for coordinating main window interactions.

    This class coordinates between UI panels and services,
    handling complex workflows like adding options, updating
    metrics, and refreshing charts.
    """

    def __init__(
        self,
        strategy_manager: StrategyManager,
        quote_service: QuoteService,
        aggregator: AggregationService,
    ) -> None:
        """Initialize the controller.

        Args:
            strategy_manager: Service for managing strategy state.
            quote_service: Service for fetching quotes.
            aggregator: Service for aggregating strategy metrics.
        """
        super().__init__()
        self.strategy_manager = strategy_manager
        self.quote_service = quote_service
        self.aggregator = aggregator
        self._logger = logging.getLogger(__name__)

        # UI components (set by MainWindow)
        self.instrument_panel: InstrumentInfoPanel | None = None
        self.metrics_panel: MetricsPanel | None = None
        self.strikes_panel: StrikesPanel | None = None
        self.chart: ChartWidget | None = None
        self.timeline: TimelineWidget | None = None

        # State
        self.expiries: list[date] = []
        self.selected_expiry: date | None = None
        self.strikes: list[float] = []

    def set_panels(
        self,
        instrument_panel: InstrumentInfoPanel,
        metrics_panel: MetricsPanel,
        strikes_panel: StrikesPanel,
        chart: ChartWidget,
        timeline: TimelineWidget,
    ) -> None:
        """Set the UI panels for the controller to manage.

        Args:
            instrument_panel: The instrument info panel.
            metrics_panel: The metrics panel.
            strikes_panel: The strikes panel.
            chart: The chart widget.
            timeline: The timeline widget.
        """
        self.instrument_panel = instrument_panel
        self.metrics_panel = metrics_panel
        self.strikes_panel = strikes_panel
        self.chart = chart
        self.timeline = timeline

    def on_symbol_changed(self, symbol: str) -> None:
        """Handle symbol change.

        Args:
            symbol: New symbol.
        """
        if not symbol:
            return

        self.load_expiries()

    def load_expiries(self, max_expiries: int = 20) -> None:
        """Load available expiries from the data service.

        Args:
            max_expiries: Maximum number of expiries to load.
        """
        all_expiries = self.quote_service.get_expiries()
        self.expiries = all_expiries[:max_expiries]
        self.selected_expiry = None

        self.update_stock_quote()
        self.render_timeline()

    def update_stock_quote(self) -> None:
        """Update price and change labels with current stock quote."""
        if self.instrument_panel is None:
            return

        symbol = self.instrument_panel.get_symbol()
        quote = self.quote_service.get_stock_quote(symbol)
        self.instrument_panel.update_quote(quote)

    def render_timeline(self) -> None:
        """Render the timeline with current expiries."""
        if self.timeline is not None:
            self.timeline.set_expiries(self.expiries)

    def on_expiry_selected(self, expiry: date) -> None:
        """Handle expiry selection.

        Args:
            expiry: Selected expiry date.
        """
        self.selected_expiry = expiry

        if self.timeline is not None:
            self.timeline.select_expiry(expiry)

        self.load_strikes_for_expiry()

    def load_strikes_for_expiry(self) -> None:
        """Load strikes for the selected expiry."""
        if self.selected_expiry is None:
            return

        if self.instrument_panel is None or self.strikes_panel is None:
            return

        symbol = self.instrument_panel.get_symbol()
        self.strikes = self.quote_service.get_strikes(symbol, self.selected_expiry)

        self.strikes_panel.set_strikes(self.strikes)

        if self.strikes:
            if symbol.upper() == "SPX":
                target = 6600.0
                nearest = min(self.strikes, key=lambda s: abs(s - target))
                self.strikes_panel.center_on_value(target)
                self.strikes_panel.set_selected_strikes([nearest])
                self.strikes_panel.set_current_price(target, "SPX")
            else:
                centre = self.strikes[len(self.strikes) // 2]
                self.strikes_panel.center_on_value(centre)
                self.strikes_panel.set_selected_strikes([centre])

    def on_add_option(self, key: str) -> None:
        """Handle add option action.

        Args:
            key: Option key (buy_call, sell_call, buy_put, sell_put).
        """
        if not self.strikes:
            return

        if self.instrument_panel is None or self.strikes_panel is None:
            return

        symbol = self.instrument_panel.get_symbol()
        centre = self.strikes[len(self.strikes) // 2]

        anchor = self.strikes_panel.get_center_strike()
        strike_chosen = float(anchor) if anchor is not None else float(centre)

        # Get spot price
        strategy = self.strategy_manager.strategy
        spot = (
            strategy.underlier.spot
            if strategy is not None
            else self.strikes_panel.get_current_price()
        )
        if spot is None:
            spot = centre

        # Get or create underlier
        underlier = (
            strategy.underlier
            if strategy is not None
            else Underlier(
                symbol=symbol or "SPX",
                spot=float(spot),
                multiplier=100,
                currency="USD",
            )
        )

        # Parse option type and side
        if key == "buy_call":
            side, otype = Side.BUY, OptionType.CALL
        elif key == "sell_call":
            side, otype = Side.SELL, OptionType.CALL
        elif key == "buy_put":
            side, otype = Side.BUY, OptionType.PUT
        elif key == "sell_put":
            side, otype = Side.SELL, OptionType.PUT
        else:
            return

        # Get expiry for new leg
        expiry_for_leg = self.strategy_manager.get_expiry_for_new_leg(
            self.selected_expiry
        )
        if expiry_for_leg is None:
            return

        # Create contract and get quote
        contract = OptionContract(
            underlier=underlier,
            expiry=expiry_for_leg,
            strike=float(strike_chosen),
            type=otype,
        )

        quote = self.quote_service.get_quote(
            symbol, expiry_for_leg, float(strike_chosen), otype
        )

        leg = OptionLeg(contract=contract, side=side, quantity=1, entry_price=quote.mid)

        # Add to strategy
        if strategy is None:
            self.strategy_manager.create_strategy("Strategy", underlier, leg)
        else:
            self.strategy_manager.add_leg(leg)

        self._logger.info(
            "Added leg: %s %s @ %.2f", side.name, otype.name, strike_chosen
        )

        self.update_metrics()
        self.update_chart()

    def on_badge_remove(self, leg_idx: int) -> None:
        """Handle badge removal.

        Args:
            leg_idx: Index of the leg to remove.
        """
        try:
            result = self.strategy_manager.remove_leg(leg_idx)
            if result is None:
                self._reset_strategy_state()
            else:
                self.update_metrics()
                self.update_chart()
        except ValueError as e:
            self._logger.warning(f"Failed to remove leg: {e}")

    def on_badge_toggle(self, leg_idx: int, new_type: OptionType) -> None:
        """Handle badge type toggle.

        Args:
            leg_idx: Index of the leg to toggle.
            new_type: New option type.
        """
        strategy = self.strategy_manager.strategy
        if strategy is None:
            return

        if leg_idx < 0 or leg_idx >= len(strategy.legs):
            return

        if self.instrument_panel is None:
            return

        symbol = self.instrument_panel.get_symbol()
        leg = strategy.legs[leg_idx]

        quote = self.quote_service.get_quote(
            symbol, leg.contract.expiry, leg.contract.strike, new_type
        )

        try:
            self.strategy_manager.update_leg_type(leg_idx, new_type, quote.mid)
            self.update_metrics()
            self.update_chart()
        except ValueError as e:
            self._logger.warning(f"Failed to toggle leg type: {e}")

    def on_badge_move(self, leg_idx: int, new_strike: float) -> None:
        """Handle badge move to new strike.

        Args:
            leg_idx: Index of the leg to move.
            new_strike: New strike price.
        """
        strategy = self.strategy_manager.strategy
        if strategy is None:
            return

        if leg_idx < 0 or leg_idx >= len(strategy.legs):
            return

        if self.instrument_panel is None:
            return

        symbol = self.instrument_panel.get_symbol()
        leg = strategy.legs[leg_idx]

        quote = self.quote_service.get_quote(
            symbol, leg.contract.expiry, float(new_strike), leg.contract.type
        )

        try:
            self.strategy_manager.update_leg_strike(leg_idx, new_strike, quote.mid)
            self._logger.info("Move leg: idx=%d strike=%.2f", leg_idx, new_strike)
            self.update_metrics()
            self.update_chart()
        except ValueError as e:
            self._logger.warning(f"Failed to move leg: {e}")

    def on_badge_preview_move(self, leg_idx: int, new_strike: float) -> None:
        """Handle badge preview move (drag preview).

        Args:
            leg_idx: Index of the leg being previewed.
            new_strike: New strike price for preview.
        """
        strategy = self.strategy_manager.strategy
        if strategy is None:
            return

        if leg_idx < 0 or leg_idx >= len(strategy.legs):
            return

        if self.instrument_panel is None:
            return

        symbol = self.instrument_panel.get_symbol()
        leg = strategy.legs[leg_idx]

        quote = self.quote_service.get_quote(
            symbol, leg.contract.expiry, float(new_strike), leg.contract.type
        )

        preview = self.strategy_manager.create_preview_strategy(
            leg_idx, new_strike, quote.mid
        )

        if preview is None:
            return

        ivs = self.quote_service.get_ivs_for_strategy(preview)
        m = self.aggregator.aggregate(preview, spot=preview.underlier.spot, ivs=ivs)

        strikes_sel = [leg_p.contract.strike for leg_p in preview.legs]
        cd = ChartPresenter.prepare(
            m,
            strike_lines=strikes_sel,
            current_price=strategy.underlier.spot,
        )

        stats = self._grid_stats(m)
        self._logger.info(
            "Preview chart: leg=%d strike=%.2f grid=%s",
            leg_idx,
            new_strike,
            stats,
        )

        if self.strikes_panel is not None:
            self.strikes_panel.set_selected_strikes(strikes_sel)

        if self.chart is not None:
            self.chart.set_chart_data(cd)
            self.chart.repaint()

    def update_metrics(self) -> None:
        """Update the metrics display."""
        strategy = self.strategy_manager.strategy
        if strategy is None:
            return

        ivs = self.quote_service.get_ivs_for_strategy(strategy)
        m = self.aggregator.aggregate(strategy, spot=strategy.underlier.spot, ivs=ivs)

        if self.metrics_panel is not None:
            pm = MetricsPresenter.prepare(m)
            self.metrics_panel.update_metrics(pm)
            self.metrics_panel.update_greeks(m, pm)

    def update_chart(self) -> None:
        """Update the chart display."""
        strategy = self.strategy_manager.strategy
        if strategy is None:
            return

        ivs = self.quote_service.get_ivs_for_strategy(strategy)

        strikes_sel: list[float] = []
        badges: list[BadgeSpec] = []

        for i, leg in enumerate(strategy.legs):
            strikes_sel.append(leg.contract.strike)
            color = (
                COLOR_SUCCESS_GREEN
                if leg.contract.type is OptionType.CALL
                else COLOR_DANGER_RED
            )
            placement = "top" if leg.side is Side.BUY else "bottom"
            text = f"{leg.side.name} {leg.contract.type.name}"
            badges.append(
                cast(
                    "BadgeSpec",
                    {
                        "strike": leg.contract.strike,
                        "text": text,
                        "color_bg": color,
                        "placement": placement,
                        "leg_idx": i,
                    },
                )
            )

        m = self.aggregator.aggregate(strategy, spot=strategy.underlier.spot, ivs=ivs)
        stats = self._grid_stats(m)

        self._logger.info(
            "Updated chart: net=%.2f be=%s grid=%s",
            m.net_debit_credit,
            m.break_evens,
            stats,
        )

        if self.strikes_panel is not None:
            self.strikes_panel.set_selected_strikes(strikes_sel)
            self.strikes_panel.set_badges(badges)

        if self.chart is not None:
            cd = ChartPresenter.prepare(
                m,
                strike_lines=strikes_sel,
                current_price=strategy.underlier.spot,
            )
            self.chart.set_chart_data(cd)
            self.chart.repaint()

    def _reset_strategy_state(self) -> None:
        """Reset strategy state and clear displays."""
        self.strategy_manager.reset()

        if self.metrics_panel is not None:
            self.metrics_panel.clear_metrics()

        if self.strikes_panel is not None:
            self.strikes_panel.set_selected_strikes([])
            self.strikes_panel.set_badges([])

        if self.chart is not None:
            self.chart.set_chart_data(
                ChartData(
                    prices=[],
                    pnls=[],
                    x_min=0.0,
                    x_max=1.0,
                    y_min=-1.0,
                    y_max=1.0,
                    strike_lines=[],
                    current_price=0.0,
                )
            )

    @staticmethod
    def _grid_stats(
        metrics: StrategyMetrics,
    ) -> tuple[int, int, float, float, float, float]:
        """Calculate grid statistics for logging.

        Args:
            metrics: Strategy metrics.

        Returns:
            Tuple of (prices_n, pnls_n, x_min, x_max, y_min, y_max).
        """
        grid = metrics.grid
        prices_n = 0 if grid is None else len(grid.prices)
        pnls_n = 0 if grid is None else len(grid.pnls)
        x_min = 0.0 if not (grid and grid.prices) else min(grid.prices)
        x_max = 0.0 if not (grid and grid.prices) else max(grid.prices)
        y_min = 0.0 if not (grid and grid.pnls) else min(grid.pnls)
        y_max = 0.0 if not (grid and grid.pnls) else max(grid.pnls)
        return prices_n, pnls_n, x_min, x_max, y_min, y_max

    def get_days_to_expiry(self) -> int | None:
        """Get days to the selected expiry.

        Returns:
            Number of days, or None if no expiry selected.
        """
        today = date.today()
        if self.selected_expiry is not None:
            return (self.selected_expiry - today).days
        if self.expiries:
            return (self.expiries[0] - today).days
        return None
