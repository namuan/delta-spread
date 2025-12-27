"""Main application window.

This module provides the main window for the Delta Spread application.
The window has been refactored to use separate panel components and a
controller for business logic.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast, override

from PyQt6.QtGui import QAction, QKeySequence

if TYPE_CHECKING:
    from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenuBar,
    QVBoxLayout,
    QWidget,
)

from mocks.options_data_mock import MockOptionsDataService
from mocks.pricing_mock import MockPricingService

from ..config import AppConfig
from ..data.database import DatabaseConnection
from ..data.trade_repository import TradeRepository
from ..data.tradier_data import TradierOptionsDataService
from ..services.aggregation import AggregationService
from ..services.async_quote_service import AsyncQuoteService
from ..services.quote_service import QuoteService
from ..services.strategy_manager import StrategyManager
from ..services.trade_service import TradeService
from ..services.workers.manager import WorkerManager
from .chart_widget import ChartWidget
from .config_dialog import ConfigDialog
from .controllers.main_window_controller import MainWindowController
from .menus.add_menu import build_add_menu
from .panels.footer_controls_panel import FooterControlsPanel
from .panels.instrument_info_panel import InstrumentInfoPanel
from .panels.metrics_panel import MetricsPanel
from .panels.strikes_panel import StrikesPanel
from .styles import (
    APP_STYLE,
    CHART_ARROW_STYLE,
    EXP_LABEL_STYLE,
)
from .timeline_widget import TimelineWidget

if TYPE_CHECKING:
    from collections.abc import Callable as TCallable
    from datetime import date

    from ..data.options_data import OptionsDataService
    from .option_badge import OptionDetailData


class MainWindow(QMainWindow):
    """Main application window.

    This class serves as the top-level container that assembles
    panels and wires up the controller to handle business logic.
    """

    def __init__(self) -> None:
        """Initialize the main window."""
        super().__init__()
        self.setWindowTitle("Delta Spread - Collapse the wave function of uncertainty")
        self.resize(1200, 850)

        self._config = AppConfig.load()
        self._logger = logging.getLogger(__name__)

        # Initialize services
        self._data_service: OptionsDataService = self._init_data_service()
        self._pricing = MockPricingService()
        self._aggregator = AggregationService(self._pricing)
        self._quote_service = QuoteService(self._data_service)
        self._strategy_manager = StrategyManager()

        # Initialize async services for background API calls
        self._worker_manager = WorkerManager()
        self._async_quote_service = AsyncQuoteService(
            self._data_service, self._worker_manager
        )

        # Initialize database and trade service
        self._database = DatabaseConnection()
        self._database.initialize_schema()
        self._trade_repository = TradeRepository(self._database)
        self._trade_service = TradeService(self._trade_repository)

        # Initialize controller with async support and trade service
        self._controller = MainWindowController(
            strategy_manager=self._strategy_manager,
            quote_service=self._quote_service,
            aggregator=self._aggregator,
            async_quote_service=self._async_quote_service,
            trade_service=self._trade_service,
        )
        self._controller.set_main_window(self)

        # Set up UI
        self._setup_central_widget()
        self._setup_menu_bar()
        self._setup_panels()
        self._wire_signals()

        # Initial data load
        self._controller.on_symbol_changed(self.instrument_panel.get_symbol())

    def _init_data_service(self) -> OptionsDataService:
        """Initialize the appropriate data service based on configuration.

        Returns:
            OptionsDataService implementation (Mock or Tradier).
        """
        if self._config.use_real_data:
            if not self._config.tradier_token:
                self._logger.warning(
                    "Real data enabled but Tradier token not configured. "
                    + "Using mock data instead."
                )
                return MockOptionsDataService()

            self._logger.info("Using Tradier real data service")
            return TradierOptionsDataService(
                symbol="SPY",
                base_url=self._config.tradier_base_url,
                token=self._config.tradier_token,
            )

        self._logger.info("Using mock data service")
        return MockOptionsDataService()

    def _setup_central_widget(self) -> None:
        """Set up the central widget and main layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setSpacing(5)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        self.setStyleSheet(APP_STYLE)

    def _setup_menu_bar(self) -> None:
        """Set up the menu bar."""
        menu_bar = self.menuBar()
        if menu_bar is None:
            menu_bar = QMenuBar(self)
            self.setMenuBar(menu_bar)

        app_menu = menu_bar.addMenu("DeltaSpread")
        if app_menu is not None:
            prefs_action = QAction("Preferences…", self)
            prefs_action.setShortcut(QKeySequence.StandardKey.Preferences)
            prefs_action.setMenuRole(QAction.MenuRole.PreferencesRole)

            connect_prefs: TCallable[..., object] = cast(
                "TCallable[..., object]", prefs_action.triggered.connect
            )
            connect_prefs(self._open_preferences)
            app_menu.addAction(prefs_action)  # type: ignore[call-overload]

    def _setup_panels(self) -> None:
        """Set up all UI panels."""
        # Instrument info panel
        self.instrument_panel = InstrumentInfoPanel()
        self.main_layout.addWidget(self.instrument_panel)

        # Add menu
        self.add_menu = build_add_menu(self, self._on_add_option)
        self.instrument_panel.set_add_menu(self.add_menu)

        # Expiration label
        self.exp_label = QLabel("EXPIRATIONS:")
        self.exp_label.setStyleSheet(EXP_LABEL_STYLE)
        self.main_layout.addWidget(self.exp_label)

        # Timeline
        self.timeline = TimelineWidget()
        self.main_layout.addWidget(self.timeline)

        # Strikes panel
        self.strikes_panel = StrikesPanel()
        self.main_layout.addWidget(self.strikes_panel)

        # Metrics panel
        self.metrics_panel = MetricsPanel()
        self.main_layout.addWidget(self.metrics_panel)

        # Chart
        chart_layout = QHBoxLayout()
        left_arrow = QLabel("<")
        left_arrow.setStyleSheet(CHART_ARROW_STYLE)
        self.chart = ChartWidget()
        right_arrow = QLabel(">")
        right_arrow.setStyleSheet(CHART_ARROW_STYLE)
        chart_layout.addWidget(left_arrow)
        chart_layout.addWidget(self.chart)
        chart_layout.addWidget(right_arrow)
        self.main_layout.addLayout(chart_layout)

        # Footer controls
        self.footer_panel = FooterControlsPanel()
        self.main_layout.addWidget(self.footer_panel)

        # Wire panels to controller
        self._controller.set_panels(
            instrument_panel=self.instrument_panel,
            metrics_panel=self.metrics_panel,
            strikes_panel=self.strikes_panel,
            chart=self.chart,
            timeline=self.timeline,
        )

    def _wire_signals(self) -> None:
        """Wire up all signals between components."""
        # Instrument panel signals
        connect_symbol: TCallable[..., object] = cast(
            "TCallable[..., object]", self.instrument_panel.symbol_changed.connect
        )
        connect_symbol(self._on_symbol_changed)

        # Trade action buttons
        connect_save: TCallable[..., object] = cast(
            "TCallable[..., object]", self.instrument_panel.save_clicked.connect
        )
        connect_save(self._controller.save_trade)

        connect_load: TCallable[..., object] = cast(
            "TCallable[..., object]", self.instrument_panel.load_clicked.connect
        )
        connect_load(self._controller.load_trade)

        connect_new: TCallable[..., object] = cast(
            "TCallable[..., object]", self.instrument_panel.new_clicked.connect
        )
        connect_new(self._controller.new_trade)

        # Timeline signals
        connect_expiry: TCallable[..., object] = cast(
            "TCallable[..., object]", self.timeline.expiry_selected.connect
        )
        connect_expiry(self._on_expiry_selected)

        # Strikes panel handlers
        self.strikes_panel.set_interaction_handlers(
            on_toggle=self._on_badge_toggle,
            on_remove=self._on_badge_remove,
            on_move=self._on_badge_move,
        )
        self.strikes_panel.set_detail_data_provider(self._get_option_detail_data)

    def _open_preferences(self) -> None:
        """Open the preferences dialog."""
        dialog = ConfigDialog(self._config, self)
        if dialog.exec():
            self._config = dialog.get_config()
            self._logger.info("Configuration updated")

            # Cancel any pending async operations
            self._async_quote_service.cancel_all()

            # Reinitialize data service with new configuration
            self._data_service = self._init_data_service()
            self._quote_service.data_service = self._data_service
            self._async_quote_service.data_service = self._data_service

            # Refresh data with new service
            self._on_symbol_changed(self.instrument_panel.get_symbol())

    def _on_symbol_changed(self, symbol: str) -> None:
        """Handle symbol change.

        Args:
            symbol: New symbol.
        """
        if not symbol:
            return

        # Reinitialize Tradier service with new symbol if using real data
        if self._config.use_real_data and isinstance(
            self._data_service, TradierOptionsDataService
        ):
            # Cancel pending async operations for old symbol
            self._async_quote_service.cancel_all()

            # Only create new data service if symbol actually changed
            # This preserves caching when reloading same symbol
            if (
                not hasattr(self._data_service, "symbol")
                or self._data_service.symbol != symbol.upper()
            ):
                self._data_service = TradierOptionsDataService(
                    symbol=symbol,
                    base_url=self._config.tradier_base_url,
                    token=self._config.tradier_token,
                )
                self._quote_service.data_service = self._data_service
                self._async_quote_service.data_service = self._data_service

        self._controller.on_symbol_changed(symbol)
        self._update_exp_label()

    def _on_expiry_selected(self, expiry: date) -> None:
        """Handle expiry selection.

        Args:
            expiry: Selected expiry date.
        """
        self._controller.on_expiry_selected(expiry)
        self._update_exp_label()

    def _update_exp_label(self) -> None:
        """Update the expiration label with days to expiry."""
        days = self._controller.get_days_to_expiry()
        if days is not None:
            self.exp_label.setText(f"EXPIRATIONS: <b>{days}d</b>")
        else:
            self.exp_label.setText("EXPIRATIONS:")

    def _on_add_option(self, key: str) -> None:
        """Handle add option action.

        Args:
            key: Option key (buy_call, sell_call, buy_put, sell_put).
        """
        self._controller.on_add_option(key)

    def _on_badge_remove(self, leg_idx: int) -> None:
        """Handle badge removal.

        Args:
            leg_idx: Index of the leg to remove.
        """
        self._controller.on_badge_remove(leg_idx)

    def _on_badge_toggle(self, leg_idx: int, new_type: object) -> None:
        """Handle badge type toggle.

        Args:
            leg_idx: Index of the leg to toggle.
            new_type: New option type.
        """
        # Import here to avoid circular imports
        from ..domain.models import OptionType  # noqa: PLC0415

        if isinstance(new_type, OptionType):
            self._controller.on_badge_toggle(leg_idx, new_type)

    def _on_badge_move(self, leg_idx: int, new_strike: float) -> None:
        """Handle badge move to new strike.

        Args:
            leg_idx: Index of the leg to move.
            new_strike: New strike price.
        """
        self._controller.on_badge_move(leg_idx, new_strike)

    def _get_option_detail_data(self, leg_idx: int) -> OptionDetailData | None:
        """Get real-time option detail data for a leg.

        Args:
            leg_idx: Index of the leg to get data for.

        Returns:
            Option detail data or None if not available.
        """
        return self._controller.get_option_detail_data(leg_idx)

    @override
    def closeEvent(self, a0: QCloseEvent | None) -> None:
        """Handle window close event.

        Properly shuts down worker threads before closing.

        Args:
            a0: The close event.
        """
        # Cancel all pending workers and wait for them to finish
        self._worker_manager.cancel_all()
        self._worker_manager.wait_for_done(timeout_ms=1000)

        # Close database connection
        self._database.close()

        if a0:
            a0.accept()
