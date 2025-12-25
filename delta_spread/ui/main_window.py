from datetime import date
import logging
from typing import TYPE_CHECKING, cast

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QMainWindow,
    QMenuBar,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from mocks.options_data_mock import MockOptionsDataService
from mocks.pricing_mock import MockPricingService

from ..config import AppConfig
from ..data.tradier_data import TradierOptionsDataService
from ..domain.models import (
    OptionContract,
    OptionLeg,
    OptionType,
    Side,
    Strategy,
    StrategyMetrics,
    Underlier,
)
from ..services.aggregation import AggregationService
from ..services.presenter import ChartData, ChartPresenter, MetricsPresenter
from .chart_widget import ChartWidget
from .config_dialog import ConfigDialog
from .menus.add_menu import build_add_menu
from .strike_ruler import StrikeRuler
from .styles import (
    APP_STYLE,
    AVERAGE_BUTTON_STYLE,
    BUTTON_PRIMARY_STYLE,
    CHANGE_LABEL_STYLE,
    CHART_ARROW_STYLE,
    COLOR_DANGER_RED,
    COLOR_GRAY_900,
    COLOR_SUCCESS_GREEN,
    DATE_SLIDER_QSS,
    EXP_LABEL_STYLE,
    IV_LABEL_STYLE,
    MARKER_LABEL_STYLE,
    METRIC_ICON_STYLE,
    METRIC_SUBTEXT_STYLE,
    METRIC_TITLE_STYLE,
    MONTH_LABEL_STYLE,
    PRICE_LABEL_STYLE,
    RANGE_SLIDER_QSS,
    REALTIME_LABEL_STYLE,
    REFRESH_LABEL_STYLE,
    RT_HELP_STYLE,
    SYMBOL_INPUT_STYLE,
)
from .timeline_widget import TimelineWidget

if TYPE_CHECKING:
    from collections.abc import Callable as TCallable

    from ..data.options_data import OptionsDataService
    from .strike_ruler import BadgeSpec


class MainWindow(QMainWindow):  # noqa: PLR0904
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Delta Spread - Collapse the wave function of uncertainty")
        self.resize(1200, 850)
        self._config = AppConfig.load()
        self._logger = logging.getLogger(__name__)
        self.data_service: OptionsDataService = self._init_data_service()
        self.pricing = MockPricingService()
        self.aggregator = AggregationService(self.pricing)
        self.expiries: list[date] = []
        self.selected_expiry: date | None = None
        self.strikes: list[float] = []
        self.strategy: Strategy | None = None
        self.metric_net_lbl: QLabel | None = None
        self.metric_max_loss_lbl: QLabel | None = None
        self.metric_max_profit_lbl: QLabel | None = None
        self.metric_pop_lbl: QLabel | None = None
        self.metric_breakevens_lbl: QLabel | None = None
        self.metric_delta_lbl: QLabel | None = None
        self.metric_theta_lbl: QLabel | None = None
        self.metric_gamma_lbl: QLabel | None = None
        self.metric_vega_lbl: QLabel | None = None
        self.metric_rho_lbl: QLabel | None = None
        self.expiry_buttons: dict[date, QPushButton] = {}
        self.price_label: QLabel | None = None
        self.change_label: QLabel | None = None
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setSpacing(5)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.setStyleSheet(APP_STYLE)
        self.setup_menu_bar()
        self.setup_instrument_info()
        self.setup_timeline()
        self.setup_strikes()
        self.setup_metrics()
        self.setup_chart()
        self.setup_footer_controls()
        self.on_symbol_changed()

    def _init_data_service(self) -> "OptionsDataService":
        """Initialize the appropriate data service based on configuration.

        Returns:
            OptionsDataService implementation (Mock or Tradier)
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
                symbol=self.symbol_input.text()
                if hasattr(self, "symbol_input")
                else "SPX",
                base_url=self._config.tradier_base_url,
                token=self._config.tradier_token,
            )

        self._logger.info("Using mock data service")
        return MockOptionsDataService()

    def setup_menu_bar(self) -> None:
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
            connect_prefs(self.open_preferences)
            app_menu.addAction(prefs_action)  # type: ignore[call-overload]

    def open_preferences(self) -> None:
        dialog = ConfigDialog(self._config, self)
        if dialog.exec():
            self._config = dialog.get_config()
            self._logger.info("Configuration updated")
            # Reinitialize data service with new configuration
            self.data_service = self._init_data_service()
            # Refresh data with new service
            self.on_symbol_changed()

    def setup_instrument_info(self) -> None:
        info_layout = QHBoxLayout()
        info_layout.setContentsMargins(0, 10, 0, 10)
        self.symbol_input = QLineEdit("SPY")
        self.symbol_input.setFixedWidth(60)
        self.symbol_input.setStyleSheet(SYMBOL_INPUT_STYLE)
        connect_return: TCallable[..., object] = cast(
            "TCallable[..., object]", self.symbol_input.returnPressed.connect
        )
        connect_return(self.on_symbol_changed)
        connect_edit: TCallable[..., object] = cast(
            "TCallable[..., object]", self.symbol_input.editingFinished.connect
        )
        connect_edit(self.on_symbol_changed)
        self.price_label = QLabel("--")
        self.price_label.setStyleSheet(PRICE_LABEL_STYLE)
        self.change_label = QLabel("--\n--")
        self.change_label.setStyleSheet(CHANGE_LABEL_STYLE)
        realtime_label = QLabel("Real-time")
        realtime_label.setStyleSheet(REALTIME_LABEL_STYLE)
        rt_help = QLabel("?")
        rt_help.setStyleSheet(RT_HELP_STYLE)
        info_layout.addWidget(self.symbol_input)
        info_layout.addSpacing(10)
        info_layout.addWidget(self.price_label)
        info_layout.addSpacing(10)
        info_layout.addWidget(self.change_label)
        info_layout.addSpacing(15)
        info_layout.addWidget(realtime_label)
        info_layout.addWidget(rt_help)
        info_layout.addStretch()
        self.btn_add = QPushButton("Add +")
        btn_pos = QPushButton("Positions")
        btn_save = QPushButton("Save Trade")
        btn_hist = QPushButton("Historical Chart")
        for btn in [self.btn_add, btn_pos, btn_save, btn_hist]:
            btn.setStyleSheet(BUTTON_PRIMARY_STYLE)
            info_layout.addWidget(btn)
        self.add_menu = build_add_menu(self, self.on_add_option)
        connect_add: TCallable[..., object] = cast(
            "TCallable[..., object]", self.btn_add.clicked.connect
        )
        connect_add(self.show_add_menu)
        self.main_layout.addLayout(info_layout)
        self.exp_label = QLabel("EXPIRATIONS:")
        self.exp_label.setStyleSheet(EXP_LABEL_STYLE)
        self.main_layout.addWidget(self.exp_label)

    def setup_timeline(self) -> None:
        self.timeline = TimelineWidget()
        connect_t: TCallable[..., object] = cast(
            "TCallable[..., object]", self.timeline.expiry_selected.connect
        )
        connect_t(self.on_expiry_selected)
        self.main_layout.addWidget(self.timeline)

    def on_symbol_changed(self) -> None:
        symbol = self.symbol_input.text().strip()
        if not symbol:
            return

        # Reinitialize Tradier service with new symbol if using real data
        if self._config.use_real_data and isinstance(
            self.data_service, TradierOptionsDataService
        ):
            self.data_service = TradierOptionsDataService(
                symbol=symbol,
                base_url=self._config.tradier_base_url,
                token=self._config.tradier_token,
            )

        self.load_expiries()

    def load_expiries(self) -> None:
        """Load available expiries from the data service."""
        all_expiries = list(self.data_service.get_expiries())
        # Limit to configured max expiries
        self.expiries = all_expiries[: self._config.max_expiries]
        self.selected_expiry = None
        self.update_stock_quote()
        self.render_timeline()

    def update_stock_quote(self) -> None:
        """Update price and change labels with current stock quote."""
        if self.price_label is None or self.change_label is None:
            return

        # Try to get real data from Tradier service
        if self._config.use_real_data and isinstance(
            self.data_service, TradierOptionsDataService
        ):
            try:
                quote = self.data_service.get_stock_quote()
                if quote:
                    # Format price with commas
                    price: float = quote["last"]
                    price_str = f"{price:,.2f}"
                    self.price_label.setText(price_str)

                    # Format change and percentage
                    change: float = quote["change"]
                    change_pct: float = quote["change_percentage"]
                    sign = "+" if change >= 0 else ""
                    change_str = f"{sign}{change_pct:.2f}%\n{sign}{change:.2f}"
                    self.change_label.setText(change_str)
                    return
            except (ValueError, KeyError, TypeError) as e:
                self._logger.warning(f"Failed to fetch stock quote: {e}")

    def update_exp_label(self) -> None:
        today = date.today()
        if self.selected_expiry is not None:
            days = (self.selected_expiry - today).days
            self.exp_label.setText(f"EXPIRATIONS: <b>{days}d</b>")
        elif self.expiries:
            days = (self.expiries[0] - today).days
            self.exp_label.setText(f"EXPIRATIONS: <b>{days}d</b>")
        else:
            self.exp_label.setText("EXPIRATIONS:")

    def render_timeline(self) -> None:
        self.timeline.set_expiries(self.expiries)

    def on_expiry_selected(self, d: date) -> None:
        self.selected_expiry = d
        self.timeline.select_expiry(d)
        self.update_exp_label()
        self.load_strikes_for_expiry()

    @staticmethod
    def _clear_layout(layout: QLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.deleteLater()
            child = item.layout()
            if child is not None:
                MainWindow._clear_layout(child)

    def setup_strikes(self) -> None:
        container = QWidget()
        container.setFixedHeight(120)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("STRIKES:")
        lbl.setStyleSheet(MONTH_LABEL_STYLE)
        layout.addWidget(lbl)
        self.strike_ruler = StrikeRuler()
        self.strike_ruler.setFixedHeight(100)
        self.strike_ruler.set_toggle_handler(self._on_badge_toggle)
        self.strike_ruler.set_remove_handler(self._on_badge_remove)
        self.strike_ruler.set_move_handler(self._on_badge_move)
        self.strike_ruler.set_preview_handler(self._on_badge_preview_move)
        layout.addWidget(self.strike_ruler)
        self.main_layout.addWidget(container)

    def load_strikes_for_expiry(self) -> None:
        if self.selected_expiry is None:
            return
        symbol = self.symbol_input.text().strip()
        self.strikes = list(self.data_service.get_strikes(symbol, self.selected_expiry))
        if hasattr(self, "strike_ruler"):
            self.strike_ruler.set_strikes(self.strikes)
            if self.strikes:
                if symbol.upper() == "SPX":
                    target = 6600.0
                    nearest = min(self.strikes, key=lambda s: abs(s - target))
                    self.strike_ruler.center_on_value(target)
                    self.strike_ruler.set_selected_strikes([nearest])
                    self.strike_ruler.set_current_price(target, "SPX")
                else:
                    centre = self.strikes[len(self.strikes) // 2]
                    self.strike_ruler.center_on_value(centre)
                    self.strike_ruler.set_selected_strikes([centre])

    def setup_metrics(self) -> None:
        metrics_container = QWidget()
        container_vlayout = QVBoxLayout(metrics_container)
        container_vlayout.setContentsMargins(0, 0, 0, 0)

        primary = self._build_primary_metrics_row()
        greeks = self._build_greeks_row()
        container_vlayout.addWidget(primary)
        container_vlayout.addWidget(greeks)
        self.main_layout.addWidget(metrics_container)

    def setup_chart(self) -> None:
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

    def show_add_menu(self) -> None:
        p = self.btn_add.mapToGlobal(self.btn_add.rect().bottomLeft())
        p = QPoint(p.x() + 8, p.y() + 4)
        self.add_menu.popup(p)

    def on_add_option(self, key: str) -> None:
        if not self.strikes:
            return
        symbol = self.symbol_input.text().strip()
        centre = self.strikes[len(self.strikes) // 2]
        anchor = (
            self.strike_ruler.get_center_strike()
            if hasattr(self, "strike_ruler")
            else None
        )
        strike_chosen = float(anchor) if anchor is not None else float(centre)
        spot = (
            self.strategy.underlier.spot
            if self.strategy is not None
            else (
                self.strike_ruler.get_current_price()
                if hasattr(self, "strike_ruler")
                else None
            )
        )
        if spot is None:
            spot = centre
        underlier = (
            self.strategy.underlier
            if self.strategy is not None
            else Underlier(
                symbol=symbol or "SPX",
                spot=float(spot),
                multiplier=100,
                currency="USD",
            )
        )
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
        strike = strike_chosen
        expiry_for_leg = (
            self.strategy.legs[0].contract.expiry
            if self.strategy is not None
            and self.strategy.constraints.same_expiry
            and self.strategy.legs
            else self.selected_expiry
        )
        if expiry_for_leg is None:
            return
        contract = OptionContract(
            underlier=underlier,
            expiry=expiry_for_leg,
            strike=float(strike),
            type=otype,
        )
        quote = self.data_service.get_quote(
            symbol, expiry_for_leg, float(strike), otype
        )
        leg = OptionLeg(contract=contract, side=side, quantity=1, entry_price=quote.mid)
        if self.strategy is None:
            self.strategy = Strategy(name="Strategy", underlier=underlier, legs=[leg])
        else:
            self.strategy = Strategy(
                name=self.strategy.name,
                underlier=self.strategy.underlier,
                legs=[*self.strategy.legs, leg],
                constraints=self.strategy.constraints,
            )
        self._logger.info("Added leg: %s %s @ %.2f", side.name, otype.name, strike)
        self.update_metrics()
        self.update_chart()

    def setup_footer_controls(self) -> None:
        controls_layout = QVBoxLayout()
        controls_layout.addLayout(self._build_date_row())
        controls_layout.addWidget(self._build_date_slider())
        controls_layout.addLayout(self._build_iv_row())
        controls_layout.addWidget(self._build_range_slider())
        controls_layout.addLayout(self._build_markers_layout())
        self.main_layout.addLayout(controls_layout)

    def update_metrics(self) -> None:
        if self.strategy is None:
            return
        ivs: dict[tuple[float, OptionType], float] = {}
        for leg in self.strategy.legs:
            q = self.data_service.get_quote(
                self.strategy.underlier.symbol,
                leg.contract.expiry,
                leg.contract.strike,
                leg.contract.type,
            )
            ivs[leg.contract.strike, leg.contract.type] = q.iv
        m = self.aggregator.aggregate(
            self.strategy, spot=self.strategy.underlier.spot, ivs=ivs
        )
        if self.metric_net_lbl:
            pm = MetricsPresenter.prepare(m)
            self.metric_net_lbl.setText(pm.net_text)
        if self.metric_max_loss_lbl:
            pm = MetricsPresenter.prepare(m)
            self.metric_max_loss_lbl.setText(pm.max_loss_text)
        if self.metric_max_profit_lbl:
            pm = MetricsPresenter.prepare(m)
            self.metric_max_profit_lbl.setText(pm.max_profit_text)
        if self.metric_breakevens_lbl:
            pm = MetricsPresenter.prepare(m)
            self.metric_breakevens_lbl.setText(pm.breakevens_text)
        if self.metric_pop_lbl:
            pm = MetricsPresenter.prepare(m)
            self.metric_pop_lbl.setText(pm.pop_text)
        self._update_greek_metrics(m)

    def _build_primary_metrics_row(self) -> QWidget:
        metrics_frame = QFrame()
        layout = QHBoxLayout(metrics_frame)
        layout.setContentsMargins(10, 10, 10, 10)
        m1, m1_lbl = self._create_metric("NET DEBIT:", "$0", "#000", "🪙")
        m2, m2_lbl = self._create_metric("MAX LOSS:", "$0", "#000", "↘")
        m3, m3_lbl = self._create_metric("MAX PROFIT:", "$0", "#22C55E", "↗")
        m4, m4_lbl = self._create_metric("CHANCE OF PROFIT:", "-", "#000", "🎲")
        m5, m5_lbl = self._create_metric("BREAKEVENS:", "-", "#000", "→")
        self.metric_net_lbl = m1_lbl
        self.metric_max_loss_lbl = m2_lbl
        self.metric_max_profit_lbl = m3_lbl
        self.metric_pop_lbl = m4_lbl
        self.metric_breakevens_lbl = m5_lbl
        layout.addWidget(m1)
        layout.addWidget(m2)
        layout.addWidget(m3)
        layout.addWidget(m4)
        layout.addWidget(m5)
        layout.addStretch()
        return metrics_frame

    def _build_greeks_row(self) -> QWidget:
        greeks_frame = QFrame()
        g_layout = QHBoxLayout(greeks_frame)
        g_layout.setContentsMargins(10, 0, 10, 10)
        g1, g1_lbl = self._create_metric("DELTA:", "-", "#000", "Δ")
        g2, g2_lbl = self._create_metric("THETA:", "-", "#000", "Θ")
        g3, g3_lbl = self._create_metric("GAMMA:", "-", "#000", "Γ")
        g4, g4_lbl = self._create_metric("VEGA:", "-", "#000", "V")
        g5, g5_lbl = self._create_metric("RHO:", "-", "#000", "R")
        self.metric_delta_lbl = g1_lbl
        self.metric_theta_lbl = g2_lbl
        self.metric_gamma_lbl = g3_lbl
        self.metric_vega_lbl = g4_lbl
        self.metric_rho_lbl = g5_lbl
        g_layout.addWidget(g1)
        g_layout.addWidget(g2)
        g_layout.addWidget(g3)
        g_layout.addWidget(g4)
        g_layout.addWidget(g5)
        g_layout.addStretch()
        return greeks_frame

    def _update_greek_metrics(self, m: StrategyMetrics) -> None:
        if self.metric_delta_lbl:
            pm = MetricsPresenter.prepare(m)
            self.metric_delta_lbl.setText(pm.delta_text)
            self.metric_delta_lbl.setStyleSheet(
                f"color: {COLOR_SUCCESS_GREEN if m.delta >= 0 else COLOR_DANGER_RED}; font-size: 14px; font-weight: bold;"
            )
        if self.metric_theta_lbl:
            pm = MetricsPresenter.prepare(m)
            self.metric_theta_lbl.setText(pm.theta_text)
            self.metric_theta_lbl.setStyleSheet(
                f"color: {COLOR_SUCCESS_GREEN if m.theta >= 0 else COLOR_DANGER_RED}; font-size: 14px; font-weight: bold;"
            )
        if self.metric_gamma_lbl:
            pm = MetricsPresenter.prepare(m)
            self.metric_gamma_lbl.setText(pm.gamma_text)
            self.metric_gamma_lbl.setStyleSheet(
                f"color: {COLOR_SUCCESS_GREEN if m.gamma >= 0 else COLOR_DANGER_RED}; font-size: 14px; font-weight: bold;"
            )
        if self.metric_vega_lbl:
            pm = MetricsPresenter.prepare(m)
            self.metric_vega_lbl.setText(pm.vega_text)
            self.metric_vega_lbl.setStyleSheet(
                f"color: {COLOR_SUCCESS_GREEN if m.vega >= 0 else COLOR_DANGER_RED}; font-size: 14px; font-weight: bold;"
            )
        if self.metric_rho_lbl:
            pm = MetricsPresenter.prepare(m)
            self.metric_rho_lbl.setText(pm.rho_text)
            self.metric_rho_lbl.setStyleSheet(
                f"color: {COLOR_GRAY_900}; font-size: 14px; font-weight: bold;"
            )

    @staticmethod
    def _create_metric(
        title: str,
        value: str,
        value_color: str,
        icon_char: str | None = None,
        subtext: str | None = None,
    ) -> tuple[QWidget, QLabel]:
        v_layout = QVBoxLayout()
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet(METRIC_TITLE_STYLE)
        val_layout = QHBoxLayout()
        if icon_char:
            icon = QLabel(icon_char)
            icon.setStyleSheet(METRIC_ICON_STYLE)
            val_layout.addWidget(icon)
        v_lbl = QLabel(value)
        v_lbl.setStyleSheet(
            f"color: {value_color}; font-size: 14px; font-weight: bold;"
        )
        val_layout.addWidget(v_lbl)
        val_layout.addStretch()
        v_layout.addWidget(t_lbl)
        v_layout.addLayout(val_layout)
        if subtext:
            s_lbl = QLabel(subtext)
            s_lbl.setStyleSheet(METRIC_SUBTEXT_STYLE)
            v_layout.addWidget(s_lbl)
        container = QWidget()
        container.setLayout(v_layout)
        return container, v_lbl

    def update_chart(self) -> None:
        if self.strategy is None:
            return
        ivs: dict[tuple[float, OptionType], float] = {}
        strikes_sel: list[float] = []
        badges: list[BadgeSpec] = []
        for i, leg in enumerate(self.strategy.legs):
            strikes_sel.append(leg.contract.strike)
            q = self.data_service.get_quote(
                self.strategy.underlier.symbol,
                leg.contract.expiry,
                leg.contract.strike,
                leg.contract.type,
            )
            ivs[leg.contract.strike, leg.contract.type] = q.iv
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
        m = self.aggregator.aggregate(
            self.strategy, spot=self.strategy.underlier.spot, ivs=ivs
        )
        stats = MainWindow._grid_stats(m)
        self._logger.info(
            "Updated chart: net=%.2f be=%s grid=%s",
            m.net_debit_credit,
            m.break_evens,
            stats,
        )
        self.strike_ruler.set_selected_strikes(strikes_sel)
        self.strike_ruler.set_badges(badges)
        cd = ChartPresenter.prepare(
            m,
            strike_lines=strikes_sel,
            current_price=self.strategy.underlier.spot,
        )
        self.chart.set_chart_data(cd)
        self.chart.repaint()

    def _on_badge_remove(self, leg_idx: int) -> None:
        if self.strategy is None:
            return
        if leg_idx < 0 or leg_idx >= len(self.strategy.legs):
            return
        legs = [leg for i, leg in enumerate(self.strategy.legs) if i != leg_idx]
        if not legs:
            self._reset_strategy_state()
            return
        self.strategy = Strategy(
            name=self.strategy.name,
            underlier=self.strategy.underlier,
            legs=legs,
            constraints=self.strategy.constraints,
        )
        self.update_metrics()
        self.update_chart()

    def _reset_strategy_state(self) -> None:
        self.strategy = None
        self._clear_metric_labels()
        self.strike_ruler.set_selected_strikes([])
        self.strike_ruler.set_badges([])
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

    def _clear_metric_labels(self) -> None:
        for lbl, val in [
            (self.metric_net_lbl, "$0"),
            (self.metric_max_loss_lbl, "$0"),
            (self.metric_max_profit_lbl, "$0"),
            (self.metric_pop_lbl, "-"),
            (self.metric_breakevens_lbl, "-"),
            (self.metric_delta_lbl, "-"),
            (self.metric_theta_lbl, "-"),
            (self.metric_gamma_lbl, "-"),
            (self.metric_vega_lbl, "-"),
            (self.metric_rho_lbl, "-"),
        ]:
            if lbl:
                lbl.setText(val)

    def _on_badge_toggle(self, leg_idx: int, new_type: OptionType) -> None:
        if self.strategy is None:
            return
        if leg_idx < 0 or leg_idx >= len(self.strategy.legs):
            return
        legs = list(self.strategy.legs)
        leg = legs[leg_idx]
        contract = OptionContract(
            underlier=leg.contract.underlier,
            expiry=leg.contract.expiry,
            strike=leg.contract.strike,
            type=new_type,
        )
        quote = self.data_service.get_quote(
            self.strategy.underlier.symbol,
            leg.contract.expiry,
            leg.contract.strike,
            new_type,
        )
        legs[leg_idx] = OptionLeg(
            contract=contract,
            side=leg.side,
            quantity=leg.quantity,
            entry_price=quote.mid,
            notes=leg.notes,
        )
        self.strategy = Strategy(
            name=self.strategy.name,
            underlier=self.strategy.underlier,
            legs=legs,
            constraints=self.strategy.constraints,
        )
        self.update_metrics()
        self.update_chart()

    def _on_badge_move(self, leg_idx: int, new_strike: float) -> None:
        if self.strategy is None:
            return
        if leg_idx < 0 or leg_idx >= len(self.strategy.legs):
            return
        legs = list(self.strategy.legs)
        leg = legs[leg_idx]
        contract = OptionContract(
            underlier=leg.contract.underlier,
            expiry=leg.contract.expiry,
            strike=float(new_strike),
            type=leg.contract.type,
        )
        quote = self.data_service.get_quote(
            self.strategy.underlier.symbol,
            leg.contract.expiry,
            float(new_strike),
            leg.contract.type,
        )
        legs[leg_idx] = OptionLeg(
            contract=contract,
            side=leg.side,
            quantity=leg.quantity,
            entry_price=quote.mid,
            notes=leg.notes,
        )
        self.strategy = Strategy(
            name=self.strategy.name,
            underlier=self.strategy.underlier,
            legs=legs,
            constraints=self.strategy.constraints,
        )
        self._logger.info("Move leg: idx=%d strike=%.2f", leg_idx, new_strike)
        self.update_metrics()
        self.update_chart()

    def _on_badge_preview_move(self, leg_idx: int, new_strike: float) -> None:
        if self.strategy is None:
            return
        if leg_idx < 0 or leg_idx >= len(self.strategy.legs):
            return
        legs = list(self.strategy.legs)
        leg = legs[leg_idx]
        contract = OptionContract(
            underlier=leg.contract.underlier,
            expiry=leg.contract.expiry,
            strike=float(new_strike),
            type=leg.contract.type,
        )
        quote = self.data_service.get_quote(
            self.strategy.underlier.symbol,
            leg.contract.expiry,
            float(new_strike),
            leg.contract.type,
        )
        legs[leg_idx] = OptionLeg(
            contract=contract,
            side=leg.side,
            quantity=leg.quantity,
            entry_price=quote.mid,
            notes=leg.notes,
        )
        s_preview = Strategy(
            name=self.strategy.name,
            underlier=self.strategy.underlier,
            legs=legs,
            constraints=self.strategy.constraints,
        )
        ivs: dict[tuple[float, OptionType], float] = {}
        for leg_p in s_preview.legs:
            q = self.data_service.get_quote(
                s_preview.underlier.symbol,
                leg_p.contract.expiry,
                leg_p.contract.strike,
                leg_p.contract.type,
            )
            ivs[leg_p.contract.strike, leg_p.contract.type] = q.iv
        m = self.aggregator.aggregate(s_preview, spot=s_preview.underlier.spot, ivs=ivs)
        strikes_sel = [leg_p.contract.strike for leg_p in s_preview.legs]
        cd = ChartPresenter.prepare(
            m,
            strike_lines=strikes_sel,
            current_price=self.strategy.underlier.spot,
        )
        stats = MainWindow._grid_stats(m)
        self._logger.info(
            "Preview chart: leg=%d strike=%.2f grid=%s",
            leg_idx,
            new_strike,
            stats,
        )
        if hasattr(self, "strike_ruler"):
            self.strike_ruler.set_selected_strikes(strikes_sel)
        if hasattr(self, "chart"):
            self.chart.set_chart_data(cd)
        self.chart.repaint()

    @staticmethod
    def _build_date_row() -> QHBoxLayout:
        row = QHBoxLayout()
        lbl_date = QLabel("DATE: <b>Now</b>")
        lbl_date.setStyleSheet("font-size: 12px;")
        lbl_remain = QLabel("(14d remaining)")
        lbl_remain.setStyleSheet("color: #555; font-size: 12px;")
        row.addWidget(lbl_date)
        row.addStretch()
        row.addWidget(lbl_remain)
        return row

    @staticmethod
    def _build_iv_row() -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 10, 0, 0)
        lbl_range = QLabel("RANGE: <b>±3.6%</b>")
        lbl_refresh = QLabel("↺")
        lbl_refresh.setStyleSheet(REFRESH_LABEL_STYLE)
        row.addWidget(lbl_range)
        row.addStretch()
        row.addWidget(lbl_refresh)
        iv_widget = QWidget()
        iv_layout = QHBoxLayout(iv_widget)
        iv_layout.setContentsMargins(0, 0, 0, 0)
        btn_avg = QPushButton("AVERAGE ▼")
        btn_avg.setStyleSheet(AVERAGE_BUTTON_STYLE)
        lbl_iv = QLabel("IMPLIED VOLATILITY: <b>18.8%</b>")
        lbl_iv.setStyleSheet(IV_LABEL_STYLE)
        iv_layout.addWidget(btn_avg)
        iv_layout.addSpacing(5)
        iv_layout.addWidget(lbl_iv)
        row.addSpacing(20)
        row.addWidget(iv_widget)
        return row

    @staticmethod
    def _grid_stats(
        metrics: StrategyMetrics,
    ) -> tuple[int, int, float, float, float, float]:
        grid = metrics.grid
        prices_n = 0 if grid is None else len(grid.prices)
        pnls_n = 0 if grid is None else len(grid.pnls)
        x_min = 0.0 if not (grid and grid.prices) else min(grid.prices)
        x_max = 0.0 if not (grid and grid.prices) else max(grid.prices)
        y_min = 0.0 if not (grid and grid.pnls) else min(grid.pnls)
        y_max = 0.0 if not (grid and grid.pnls) else max(grid.pnls)
        return prices_n, pnls_n, x_min, x_max, y_min, y_max

    @staticmethod
    def _build_markers_layout() -> QHBoxLayout:
        markers = QHBoxLayout()
        m1 = QLabel("x1")
        m2 = QLabel("x2")
        m3 = QLabel("x3")
        for m in [m1, m2, m3]:
            m.setStyleSheet(MARKER_LABEL_STYLE)
        markers.addWidget(m1)
        markers.addStretch()
        markers.addWidget(m2)
        markers.addStretch()
        markers.addWidget(m3)
        return markers

    @staticmethod
    def _build_date_slider() -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setStyleSheet(DATE_SLIDER_QSS)
        return slider

    @staticmethod
    def _build_range_slider() -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setValue(30)
        slider.setStyleSheet(RANGE_SLIDER_QSS)
        return slider

    def setup_bottom_tabs(self) -> None:
        pass
