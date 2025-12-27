"""Main window controller.

This module provides a controller that coordinates between
UI panels and services, handling complex workflows and
state transitions.
"""

from __future__ import annotations

from dataclasses import dataclass
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

# Constants
STRIKE_TOLERANCE = 0.01  # Tolerance for comparing strike prices

if TYPE_CHECKING:
    from collections.abc import Callable as TCallable

    from PyQt6.QtWidgets import QMainWindow

    from ...data.tradier_data import StockQuote
    from ...domain.models import OptionQuote, Strategy, StrategyMetrics
    from ...services.aggregation import AggregationService
    from ...services.async_quote_service import AsyncQuoteService
    from ...services.quote_service import QuoteService
    from ...services.strategy_manager import StrategyManager
    from ...services.trade_service import TradeServiceProtocol
    from ..chart_widget import ChartWidget
    from ..option_badge import OptionDetailData
    from ..panels.instrument_info_panel import InstrumentInfoPanel
    from ..panels.metrics_panel import MetricsPanel
    from ..panels.strikes_panel import StrikesPanel
    from ..strike_ruler import BadgeSpec
    from ..timeline_widget import TimelineWidget


@dataclass
class PendingAddOption:
    """Context for a pending async add option operation."""

    contract: OptionContract
    side: Side
    underlier: Underlier
    is_new_strategy: bool


@dataclass
class PendingToggle:
    """Context for a pending async toggle operation."""

    leg_idx: int
    new_type: OptionType
    expiry: date
    strike: float


@dataclass
class PendingMove:
    """Context for a pending async move operation."""

    leg_idx: int
    new_strike: float
    expiry: date
    option_type: OptionType


@dataclass
class PendingExpiryChange:
    """Context for a pending async expiry change operation."""

    leg_idx: int
    new_expiry: date
    strike: float
    option_type: OptionType


class MainWindowController:
    """Controller for coordinating main window interactions.

    This class coordinates between UI panels and services,
    handling complex workflows like adding options, updating
    metrics, and refreshing charts.

    All API operations use the async quote service via background workers.
    """

    def __init__(
        self,
        strategy_manager: StrategyManager,
        quote_service: QuoteService,
        aggregator: AggregationService,
        async_quote_service: AsyncQuoteService,
        trade_service: TradeServiceProtocol | None = None,
    ) -> None:
        """Initialize the controller.

        Args:
            strategy_manager: Service for managing strategy state.
            quote_service: Service for fetching quotes (sync).
            aggregator: Service for aggregating strategy metrics.
            async_quote_service: Async quote service for background API calls.
            trade_service: Optional service for saving/loading trades.
        """
        super().__init__()
        self.strategy_manager = strategy_manager
        self.quote_service = quote_service
        self.aggregator = aggregator
        self.async_quote_service = async_quote_service
        self.trade_service = trade_service
        self._logger = logging.getLogger(__name__)
        self._main_window: QMainWindow | None = None

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

        # Loading state
        self._is_loading = False
        self._max_expiries = 20

        # Trade persistence state
        self._current_trade_id: int | None = None

        # Pending async operations
        self._pending_add_option: PendingAddOption | None = None
        self._pending_toggle: PendingToggle | None = None
        self._pending_move: PendingMove | None = None
        self._pending_expiry_changes: list[PendingExpiryChange] = []

        # Wire async signals
        self._connect_async_signals()

    def _connect_async_signals(self) -> None:
        """Connect signals from the async quote service."""
        svc = self.async_quote_service
        connect_expiries = cast("TCallable[..., object]", svc.expiries_loaded.connect)
        connect_strikes = cast("TCallable[..., object]", svc.strikes_loaded.connect)
        connect_stock = cast("TCallable[..., object]", svc.stock_quote_loaded.connect)
        connect_quote = cast("TCallable[..., object]", svc.quote_loaded.connect)
        connect_error = cast("TCallable[..., object]", svc.error_occurred.connect)
        connect_started = cast("TCallable[..., object]", svc.loading_started.connect)
        connect_finished = cast("TCallable[..., object]", svc.loading_finished.connect)

        connect_expiries(self._on_expiries_loaded)
        connect_strikes(self._on_strikes_loaded)
        connect_stock(self._on_stock_quote_loaded)
        connect_quote(self._on_quote_loaded)
        connect_error(self._on_async_error)
        connect_started(self._on_loading_started)
        connect_finished(self._on_loading_finished)

    def _on_expiries_loaded(self, expiries: list[date]) -> None:
        """Handle expiries loaded from background thread.

        Args:
            expiries: List of available expiry dates.
        """
        self.expiries = expiries[: self._max_expiries]
        self.selected_expiry = None
        self.render_timeline()

        # Chain: fetch stock quote after expiries
        if self.instrument_panel is not None:
            symbol = self.instrument_panel.get_symbol()
            self.async_quote_service.fetch_stock_quote(symbol)

    def _on_strikes_loaded(
        self, symbol: str, expiry: date, strikes: list[float]
    ) -> None:
        """Handle strikes loaded from background thread.

        Args:
            symbol: The symbol these strikes are for.
            expiry: The expiry these strikes are for.
            strikes: List of available strike prices.
        """
        # Verify this is still the selected expiry
        if expiry != self.selected_expiry:
            self._logger.debug(
                "Ignoring strikes for stale expiry: %s (current: %s)",
                expiry,
                self.selected_expiry,
            )
            return

        self.strikes = strikes

        self._logger.info(
            "load_strikes_for_expiry: symbol=%s, num_strikes=%d",
            symbol,
            len(self.strikes),
        )

        if self.strikes_panel is not None:
            self.strikes_panel.set_strikes(self.strikes)

        if self.strikes:
            # Center on current price - need to fetch stock quote
            self.async_quote_service.fetch_stock_quote(symbol)

    def _on_stock_quote_loaded(self, symbol: str, quote: StockQuote | None) -> None:
        """Handle stock quote loaded from background thread.

        Args:
            symbol: The symbol this quote is for.
            quote: The stock quote data or None if unavailable.
        """
        if self.instrument_panel is not None:
            self.instrument_panel.update_quote(quote)

        # If we have strikes loaded, center on the current price
        if self.strikes and self.strikes_panel is not None and quote is not None:
            current_price = quote["last"]
            nearest = min(self.strikes, key=lambda s: abs(s - current_price))
            self._logger.info(
                "load_strikes_for_expiry: current_price=%.2f, nearest_strike=%.2f, calling center_on_value",
                current_price,
                nearest,
            )
            self.strikes_panel.center_on_value(current_price)
            self.strikes_panel.set_selected_strikes([nearest])
            self.strikes_panel.set_current_price(current_price, symbol.upper())

    def _on_quote_loaded(
        self,
        _symbol: str,
        expiry: date,
        strike: float,
        option_type: OptionType,
        quote: OptionQuote,
    ) -> None:
        """Handle option quote loaded from background thread.

        Args:
            _symbol: The underlying symbol (unused, for signal signature).
            expiry: The expiry date.
            strike: The strike price.
            option_type: CALL or PUT.
            quote: The option quote.
        """
        # Try to complete pending add option
        if self._complete_pending_add(expiry, strike, option_type, quote):
            return

        # Try to complete pending toggle
        if self._complete_pending_toggle(expiry, strike, option_type, quote):
            return

        # Try to complete pending move
        if self._complete_pending_move(expiry, strike, option_type, quote):
            return

        # Try to complete pending expiry changes
        self._complete_pending_expiry_change(expiry, strike, option_type, quote)

    def _complete_pending_add(
        self,
        expiry: date,
        strike: float,
        option_type: OptionType,
        quote: OptionQuote,
    ) -> bool:
        """Complete a pending add option operation.

        Returns:
            True if a pending add was completed, False otherwise.
        """
        pending = self._pending_add_option
        if pending is None:
            return False

        contract = pending.contract
        if (
            contract.expiry != expiry
            or contract.strike != strike
            or contract.type != option_type
        ):
            return False

        # Clear pending state
        self._pending_add_option = None

        # Create leg and add to strategy
        leg = OptionLeg(
            contract=contract,
            side=pending.side,
            quantity=1,
            entry_price=quote.mid,
        )

        if pending.is_new_strategy:
            self.strategy_manager.create_strategy("Strategy", pending.underlier, leg)
        else:
            self.strategy_manager.add_leg(leg)

        self._logger.info(
            "Added leg: %s %s @ %.2f",
            pending.side.name,
            option_type.name,
            strike,
        )

        self.update_metrics()
        self.update_chart()
        return True

    def _complete_pending_toggle(
        self,
        expiry: date,
        strike: float,
        option_type: OptionType,
        quote: OptionQuote,
    ) -> bool:
        """Complete a pending toggle operation.

        Returns:
            True if a pending toggle was completed, False otherwise.
        """
        pending = self._pending_toggle
        if pending is None:
            return False

        if (
            pending.expiry != expiry
            or pending.strike != strike
            or pending.new_type != option_type
        ):
            return False

        # Clear pending state
        self._pending_toggle = None

        try:
            self.strategy_manager.update_leg_type(
                pending.leg_idx, pending.new_type, quote.mid
            )
            self.update_metrics()
            self.update_chart()
        except ValueError as e:
            self._logger.warning("Failed to toggle leg type: %s", e)

        return True

    def _complete_pending_move(
        self,
        expiry: date,
        strike: float,
        option_type: OptionType,
        quote: OptionQuote,
    ) -> bool:
        """Complete a pending move operation.

        Returns:
            True if a pending move was completed, False otherwise.
        """
        pending = self._pending_move
        if pending is None:
            return False

        if (
            pending.expiry != expiry
            or pending.new_strike != strike
            or pending.option_type != option_type
        ):
            return False

        # Clear pending state
        self._pending_move = None

        try:
            self.strategy_manager.update_leg_strike(
                pending.leg_idx, pending.new_strike, quote.mid
            )
            self._logger.info(
                "Move leg: idx=%d strike=%.2f", pending.leg_idx, pending.new_strike
            )
            self.update_metrics()
            self.update_chart()
        except ValueError as e:
            self._logger.warning("Failed to move leg: %s", e)

        return True

    def _complete_pending_expiry_change(
        self,
        expiry: date,
        strike: float,
        option_type: OptionType,
        quote: OptionQuote,
    ) -> bool:
        """Complete a pending expiry change operation.

        Returns:
            True if a pending expiry change was completed, False otherwise.
        """
        # Find matching pending expiry change
        matching_idx: int | None = None
        for i, pending in enumerate(self._pending_expiry_changes):
            if (
                pending.new_expiry == expiry
                and pending.strike == strike
                and pending.option_type == option_type
            ):
                matching_idx = i
                break

        if matching_idx is None:
            return False

        pending = self._pending_expiry_changes.pop(matching_idx)

        try:
            self.strategy_manager.update_leg_expiry(
                pending.leg_idx, pending.new_expiry, quote.mid
            )
            self._logger.info(
                "Updated leg %d expiry to %s with price %.2f",
                pending.leg_idx,
                pending.new_expiry,
                quote.mid,
            )

            # Only update UI if all pending expiry changes are complete
            if not self._pending_expiry_changes:
                self.update_metrics()
                self.update_chart()
        except ValueError as e:
            self._logger.warning("Failed to update leg expiry: %s", e)

        return True

    def _on_async_error(self, request_id: str, error: Exception) -> None:
        """Handle async API error.

        Args:
            request_id: The request that failed.
            error: The exception that occurred.
        """
        self._logger.error("API error (request=%s): %s", request_id, error)
        # Could show error to user via status bar or dialog here

    def _on_loading_started(self, operation: str) -> None:
        """Handle loading started signal.

        Args:
            operation: The type of operation that started.
        """
        self._is_loading = True
        self._logger.debug("Loading started: %s", operation)
        if self.instrument_panel is not None:
            self.instrument_panel.show_loading()

    def _on_loading_finished(self, operation: str) -> None:
        """Handle loading finished signal.

        Args:
            operation: The type of operation that finished.
        """
        if not self.async_quote_service.is_loading:
            self._is_loading = False
            if self.instrument_panel is not None:
                self.instrument_panel.hide_loading()
        self._logger.debug("Loading finished: %s", operation)

    @property
    def is_loading(self) -> bool:
        """Check if any async operations are in progress."""
        return self._is_loading

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

        Uses async service if available, otherwise falls back to sync.

        Args:
            max_expiries: Maximum number of expiries to load.
        """
        self._max_expiries = max_expiries

        # Always use async service
        self.async_quote_service.fetch_expiries()

    def update_stock_quote(self) -> None:
        """Update price and change labels with current stock quote."""
        if self.instrument_panel is None:
            return

        symbol = self.instrument_panel.get_symbol()

        # Always use async service
        self.async_quote_service.fetch_stock_quote(symbol)

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

        # Update existing strategy legs to the new expiry
        self._update_strategy_legs_expiry(expiry)

    def _update_strategy_legs_expiry(self, new_expiry: date) -> None:
        """Update all strategy legs to a new expiry date.

        Fetches new prices for each leg at the new expiry.

        Args:
            new_expiry: The new expiry date for all legs.
        """
        strategy = self.strategy_manager.strategy
        if strategy is None:
            return

        if self.instrument_panel is None:
            return

        # Check if expiry actually changed
        if strategy.legs and strategy.legs[0].contract.expiry == new_expiry:
            return

        symbol = self.instrument_panel.get_symbol()

        # Clear any existing pending expiry changes
        self._pending_expiry_changes.clear()

        # Queue up expiry change requests for each leg
        for leg_idx, leg in enumerate(strategy.legs):
            pending = PendingExpiryChange(
                leg_idx=leg_idx,
                new_expiry=new_expiry,
                strike=leg.contract.strike,
                option_type=leg.contract.type,
            )
            self._pending_expiry_changes.append(pending)

            # Fetch quote for the leg at new expiry using async service
            self.async_quote_service.fetch_quote(
                symbol,
                new_expiry,
                leg.contract.strike,
                leg.contract.type,
            )

    def load_strikes_for_expiry(self) -> None:
        """Load strikes for the selected expiry."""
        if self.selected_expiry is None:
            return

        if self.instrument_panel is None or self.strikes_panel is None:
            return

        symbol = self.instrument_panel.get_symbol()

        # Always use async service
        self.async_quote_service.fetch_strikes(symbol, self.selected_expiry)
        # Pre-fetch the full option chain to populate cache
        self.async_quote_service.fetch_chain(symbol, self.selected_expiry)

    @staticmethod
    def _parse_option_key(key: str) -> tuple[Side, OptionType] | None:
        """Parse option key into side and type.

        Args:
            key: Option key (buy_call, sell_call, buy_put, sell_put).

        Returns:
            Tuple of (Side, OptionType) or None if invalid key.
        """
        key_map: dict[str, tuple[Side, OptionType]] = {
            "buy_call": (Side.BUY, OptionType.CALL),
            "sell_call": (Side.SELL, OptionType.CALL),
            "buy_put": (Side.BUY, OptionType.PUT),
            "sell_put": (Side.SELL, OptionType.PUT),
        }
        return key_map.get(key)

    def _get_add_option_context(
        self,
    ) -> tuple[str, float, Underlier, bool] | None:
        """Get context needed for adding an option.

        Returns:
            Tuple of (symbol, strike, underlier, is_new_strategy) or None.
        """
        if self.instrument_panel is None or self.strikes_panel is None:
            return None

        symbol = self.instrument_panel.get_symbol()
        centre = self.strikes[len(self.strikes) // 2]

        anchor = self.strikes_panel.get_center_strike()
        strike_chosen = float(anchor) if anchor is not None else float(centre)

        strategy = self.strategy_manager.strategy
        spot = (
            strategy.underlier.spot
            if strategy is not None
            else self.strikes_panel.get_current_price()
        )
        if spot is None:
            spot = centre

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

        return (symbol, strike_chosen, underlier, strategy is None)

    def on_add_option(self, key: str) -> None:
        """Handle add option action.

        Args:
            key: Option key (buy_call, sell_call, buy_put, sell_put).
        """
        if not self.strikes:
            return

        parsed = self._parse_option_key(key)
        if parsed is None:
            return
        side, otype = parsed

        context = self._get_add_option_context()
        if context is None:
            return
        symbol, strike_chosen, underlier, is_new_strategy = context

        expiry_for_leg = self.strategy_manager.get_expiry_for_new_leg(
            self.selected_expiry
        )
        if expiry_for_leg is None:
            return

        contract = OptionContract(
            underlier=underlier,
            expiry=expiry_for_leg,
            strike=float(strike_chosen),
            type=otype,
        )

        # Always use async service
        self._pending_add_option = PendingAddOption(
            contract=contract,
            side=side,
            underlier=underlier,
            is_new_strategy=is_new_strategy,
        )
        self.async_quote_service.fetch_quote(
            symbol, expiry_for_leg, float(strike_chosen), otype
        )

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

        # Always use async service
        self._pending_toggle = PendingToggle(
            leg_idx=leg_idx,
            new_type=new_type,
            expiry=leg.contract.expiry,
            strike=leg.contract.strike,
        )
        self.async_quote_service.fetch_quote(
            symbol, leg.contract.expiry, leg.contract.strike, new_type
        )

    def on_badge_move(self, leg_idx: int, new_strike: float) -> None:
        """Handle badge move to new strike.

        All API calls execute in background workers, even when accessing cached data.

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

        # Always use async service - executes in background worker (uses cached chain data)
        self._pending_move = PendingMove(
            leg_idx=leg_idx,
            new_strike=float(new_strike),
            expiry=leg.contract.expiry,
            option_type=leg.contract.type,
        )
        self.async_quote_service.fetch_quote(
            symbol, leg.contract.expiry, float(new_strike), leg.contract.type
        )

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

    def get_option_detail_data(self, leg_idx: int) -> OptionDetailData | None:
        """Get real-time option detail data for a leg.

        Note: Uses sync API because caller expects immediate return value for tooltip.
        Consider refactoring to async with callback if this becomes a performance issue.

        Args:
            leg_idx: Index of the leg to get data for.

        Returns:
            Option detail data or None if not available.
        """
        strategy = self.strategy_manager.strategy
        if strategy is None:
            return None

        if leg_idx < 0 or leg_idx >= len(strategy.legs):
            return None

        if self.instrument_panel is None:
            return None

        leg = strategy.legs[leg_idx]
        symbol = self.instrument_panel.get_symbol()

        # Format expiration date
        exp_str = leg.contract.expiry.strftime("%m/%d/%y")

        # Format strike string with C/P suffix
        strike_str = (
            f"{leg.contract.strike:.0f}C"
            if leg.contract.type is OptionType.CALL
            else f"{leg.contract.strike:.0f}P"
        )

        # Try to get detailed option data first (includes volume, OI, and real greeks)
        details = self.quote_service.get_option_details(
            symbol,
            leg.contract.expiry,
            leg.contract.strike,
            leg.contract.type,
        )

        if details is not None:
            # Use real-time data from Tradier
            from ..option_badge import OptionDetailData  # noqa: PLC0415

            return OptionDetailData(
                symbol=symbol.upper(),
                strike=strike_str,
                expiration=exp_str,
                price=float(cast("float | str | int", details.get("mid", 0))),
                bid=float(cast("float | str | int", details.get("bid", 0))),
                ask=float(cast("float | str | int", details.get("ask", 0))),
                volume=int(cast("float | str | int", details.get("volume", 0))),
                oi=int(cast("float | str | int", details.get("oi", 0))),
                iv=f"{float(cast("float | str | int", details.get("iv", 0))) * 100:.1f}%",
                delta=float(cast("float | str | int", details.get("delta", 0))),
                theta=float(cast("float | str | int", details.get("theta", 0))),
                gamma=float(cast("float | str | int", details.get("gamma", 0))),
                vega=float(cast("float | str | int", details.get("vega", 0))),
                rho=float(cast("float | str | int", details.get("rho", 0))),
            )

        # Fallback to basic quote and calculated greeks
        try:
            quote = self.quote_service.get_quote(
                symbol,
                leg.contract.expiry,
                leg.contract.strike,
                leg.contract.type,
            )
        except (ValueError, KeyError) as e:
            self._logger.warning(f"Failed to fetch quote for leg {leg_idx}: {e}")
            return None

        # Calculate greeks using the pricing service
        iv = quote.iv if quote.iv > 0 else 0.2  # Default IV if not available
        metrics = self.aggregator.pricing_service.price_and_greeks(
            leg, strategy.underlier.spot, iv
        )

        # Import here to avoid circular imports
        from ..option_badge import OptionDetailData  # noqa: PLC0415

        return OptionDetailData(
            symbol=symbol.upper(),
            strike=strike_str,
            expiration=exp_str,
            price=quote.mid,
            bid=quote.bid,
            ask=quote.ask,
            volume=0,  # Not available from basic quote
            oi=0,  # Not available from basic quote
            iv=f"{quote.iv * 100:.1f}%",
            delta=metrics.delta,
            theta=metrics.theta,
            gamma=metrics.gamma,
            vega=metrics.vega,
            rho=0.0,  # Not calculated by current pricing service
        )

    def set_main_window(self, window: QMainWindow) -> None:
        """Set the main window reference for dialogs.

        Args:
            window: The main window instance.
        """
        self._main_window = window

    def save_trade(self) -> None:
        """Save or update current positions as a trade.

        If editing an existing trade (has _current_trade_id), updates it.
        Otherwise, shows save dialog for new trade.
        """
        if self.trade_service is None:
            self._logger.warning("Trade service not available")
            return

        if not self.strategy_manager.has_strategy():
            self._show_message("No positions to save", is_error=True)
            return

        strategy = self.strategy_manager.strategy
        if strategy is None:
            return

        # If we have a current trade ID, update the existing trade
        if self._current_trade_id is not None:
            try:
                self.trade_service.update_trade(
                    self._current_trade_id, strategy, notes=None
                )
                self._show_message(f"Trade '{strategy.name}' updated")
            except ValueError as e:
                self._show_message(str(e), is_error=True)
            return

        # Import here to avoid circular imports
        from ..dialogs.save_trade_dialog import SaveTradeDialog  # noqa: PLC0415

        dialog = SaveTradeDialog(strategy, self.trade_service, self._main_window)
        if dialog.exec():
            name, notes = dialog.get_save_data()
            try:
                trade_id = self.trade_service.save_trade(strategy, name, notes)
                self._current_trade_id = trade_id
                self._show_message(f"Trade '{name}' saved successfully")
            except ValueError as e:
                self._show_message(str(e), is_error=True)

    def load_trade(self) -> None:
        """Show load dialog and restore selected trade."""
        if self.trade_service is None:
            self._logger.warning("Trade service not available")
            return

        # Import here to avoid circular imports
        from ..dialogs.load_trade_dialog import LoadTradeDialog  # noqa: PLC0415

        dialog = LoadTradeDialog(
            self.trade_service,
            self._main_window,
            current_trade_id=self._current_trade_id,
        )
        if dialog.exec():
            trade_id = dialog.get_selected_trade_id()
            if trade_id is not None:
                strategy = self.trade_service.load_trade(trade_id)
                if strategy:
                    self.strategy_manager.strategy = strategy
                    self._current_trade_id = trade_id
                    self._refresh_ui_after_load(strategy)
                    self._show_message(f"Trade '{strategy.name}' loaded")

    def new_trade(self) -> None:
        """Clear current positions and start a new trade."""
        self.strategy_manager.strategy = None
        self._current_trade_id = None
        self.expiries = []
        self.selected_expiry = None
        self.strikes = []

        # Reset UI components
        if self.instrument_panel is not None:
            self.instrument_panel.set_symbol("")
            self.instrument_panel.update_price("--")
            self.instrument_panel.update_change("--")
            self.instrument_panel.clear_message()

        if self.timeline is not None:
            self.timeline.set_expiries([])

        if self.strikes_panel is not None:
            self.strikes_panel.set_strikes([])
            self.strikes_panel.set_badges([])  # Clear position badges

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

        if self.metrics_panel is not None:
            self.metrics_panel.clear_metrics()

        self._logger.info("Started new trade")

    def _refresh_ui_after_load(self, strategy: Strategy) -> None:
        """Refresh the UI after loading a trade.

        Args:
            strategy: The loaded strategy.
        """
        # Update instrument panel with symbol and emit signal to trigger
        # full refresh (data service reinitialization, expiries, stock quote)
        if self.instrument_panel is not None:
            # Show stored price temporarily until live quote arrives
            self.instrument_panel.update_price(f"${strategy.underlier.spot:.2f}")
            # Set symbol and emit signal to trigger full data refresh
            self.instrument_panel.set_symbol(
                strategy.underlier.symbol, emit_signal=True
            )

        # Update chart and metrics
        self.update_chart()
        self.update_metrics()

    def _show_message(self, message: str, *, is_error: bool = False) -> None:
        """Show a message to the user inline in the instrument panel.

        Args:
            message: The message to display.
            is_error: Whether this is an error message.
        """
        if self.instrument_panel is not None:
            self.instrument_panel.show_message(message, is_error=is_error)
        else:
            self._logger.info("Message: %s", message)
