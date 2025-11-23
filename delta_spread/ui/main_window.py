from datetime import date
import logging
from typing import TYPE_CHECKING, cast

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from mocks.options_data_mock import MockOptionsDataService
from mocks.pricing_mock import MockPricingService

from ..domain.models import (
    OptionContract,
    OptionLeg,
    OptionType,
    Side,
    Strategy,
    Underlier,
)
from ..services.aggregation import AggregationService
from ..services.presenter import ChartPresenter, MetricsPresenter
from .chart_widget import ChartWidget
from .menus.add_menu import build_add_menu
from .strike_ruler import StrikeRuler
from .styles import (
    APP_STYLE,
    AVERAGE_BUTTON_STYLE,
    BUTTON_PRIMARY_STYLE,
    CHANGE_LABEL_STYLE,
    CHART_ARROW_STYLE,
    COLOR_DANGER_RED,
    COLOR_SUCCESS_GREEN,
    DATE_SLIDER_QSS,
    DAY_BTN_SELECTED_STYLE,
    DAY_BTN_STYLE,
    EXP_LABEL_STYLE,
    HLINE_STYLE,
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
    TIMELINE_FRAME_STYLE,
)

if TYPE_CHECKING:
    from collections.abc import Callable as TCallable

    from ..services.options_data import OptionsDataService
    from .strike_ruler import BadgeSpec


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Delta Spread - Collapse the wave function of uncertainty")
        self.resize(1200, 850)
        self.data_service: OptionsDataService = MockOptionsDataService()
        self._logger = logging.getLogger(__name__)
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
        self.expiry_buttons: dict[date, QPushButton] = {}
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setSpacing(5)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.setStyleSheet(APP_STYLE)
        self.setup_instrument_info()
        self.setup_timeline()
        self.setup_strikes()
        self.setup_metrics()
        self.setup_chart()
        self.setup_footer_controls()
        self.on_symbol_changed()

    def setup_instrument_info(self) -> None:
        info_layout = QHBoxLayout()
        info_layout.setContentsMargins(0, 10, 0, 10)
        self.symbol_input = QLineEdit("SPX")
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
        price_label = QLabel("6,602.99")
        price_label.setStyleSheet(PRICE_LABEL_STYLE)
        change_label = QLabel("+0.98%\n+64.23")
        change_label.setStyleSheet(CHANGE_LABEL_STYLE)
        realtime_label = QLabel("Real-time")
        realtime_label.setStyleSheet(REALTIME_LABEL_STYLE)
        rt_help = QLabel("?")
        rt_help.setStyleSheet(RT_HELP_STYLE)
        info_layout.addWidget(self.symbol_input)
        info_layout.addSpacing(10)
        info_layout.addWidget(price_label)
        info_layout.addSpacing(10)
        info_layout.addWidget(change_label)
        info_layout.addSpacing(15)
        info_layout.addWidget(realtime_label)
        info_layout.addWidget(rt_help)
        info_layout.addStretch()
        self.btn_add = QPushButton("Add +")
        btn_pos = QPushButton("Positions (2)")
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
        self.timeline_frame = QFrame()
        self.timeline_frame.setStyleSheet(TIMELINE_FRAME_STYLE)
        self.timeline_layout = QVBoxLayout(self.timeline_frame)
        self.timeline_layout.setContentsMargins(0, 0, 0, 0)
        self.timeline_layout.setSpacing(0)
        self.month_layout = QHBoxLayout()
        self.month_layout.setContentsMargins(10, 2, 10, 2)
        self.timeline_layout.addLayout(self.month_layout)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(HLINE_STYLE)
        self.timeline_layout.addWidget(line)
        self.days_layout = QHBoxLayout()
        self.days_layout.setContentsMargins(5, 2, 5, 2)
        self.days_layout.setSpacing(15)
        self.timeline_layout.addLayout(self.days_layout)
        self.main_layout.addWidget(self.timeline_frame)

    def on_symbol_changed(self) -> None:
        symbol = self.symbol_input.text().strip()
        if not symbol:
            return
        self.load_expiries()

    def load_expiries(self) -> None:
        self.expiries = list(self.data_service.get_expiries())
        self.update_exp_label()
        self.render_timeline()

    def update_exp_label(self) -> None:
        today = date.today()
        parts = [f"{(d - today).days}d" for d in self.expiries]
        self.exp_label.setText(f"EXPIRATIONS: <b>{", ".join(parts)}</b>")

    def render_timeline(self) -> None:
        self._clear_layout(self.month_layout)
        self._clear_layout(self.days_layout)
        months: list[str] = []
        for d in self.expiries:
            m = d.strftime("%b")
            if m not in months:
                months.append(m)
        for m in months:
            lbl = QLabel(m)
            lbl.setStyleSheet(MONTH_LABEL_STYLE)
            self.month_layout.addWidget(lbl)
            self.month_layout.addStretch()
        self.expiry_buttons = {}
        for d in self.expiries:
            btn = QPushButton(d.strftime("%d"))
            btn.setStyleSheet(DAY_BTN_STYLE)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            connect_btn: TCallable[..., object] = cast(
                "TCallable[..., object]", btn.clicked.connect
            )
            connect_btn(lambda _=False, dd=d: self.on_expiry_selected(dd))
            self.days_layout.addWidget(btn)
            self.expiry_buttons[d] = btn
        self.days_layout.addStretch()
        if self.expiries:
            self.on_expiry_selected(self.expiries[0])

    def on_expiry_selected(self, d: date) -> None:
        self.selected_expiry = d
        for ed, btn in self.expiry_buttons.items():
            if ed == d:
                btn.setStyleSheet(DAY_BTN_SELECTED_STYLE)
            else:
                btn.setStyleSheet(DAY_BTN_STYLE)
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
        layout.addWidget(self.strike_ruler)
        self.main_layout.addWidget(container)

    def load_strikes_for_expiry(self) -> None:
        if self.selected_expiry is None:
            return
        symbol = self.symbol_input.text().strip()
        self.strikes = list(self.data_service.get_strikes(symbol, self.selected_expiry))
        if hasattr(self, "strike_ruler"):
            self.strike_ruler.set_strikes(self.strikes)

    def setup_metrics(self) -> None:
        metrics_frame = QFrame()
        layout = QHBoxLayout(metrics_frame)
        layout.setContentsMargins(10, 10, 10, 10)

        def create_metric(
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

        m1, m1_lbl = create_metric("NET DEBIT:", "$0", "#000", "🪙")
        m2, m2_lbl = create_metric("MAX LOSS:", "$0", "#000", "↘")
        m3, m3_lbl = create_metric("MAX PROFIT:", "$0", "#22C55E", "↗")
        m4, m4_lbl = create_metric("CHANCE OF PROFIT:", "-", "#000", "🎲")
        m5, m5_lbl = create_metric("BREAKEVENS:", "-", "#000", "→")
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
        self.main_layout.addWidget(metrics_frame)

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
        if self.selected_expiry is None:
            return
        if not self.strikes:
            return
        symbol = self.symbol_input.text().strip()
        centre = self.strikes[len(self.strikes) // 2]
        spot = centre
        underlier = Underlier(
            symbol=symbol or "SPX", spot=float(spot), multiplier=100, currency="USD"
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
        strike = min(self.strikes, key=lambda s: abs(s - spot))
        contract = OptionContract(
            underlier=underlier,
            expiry=self.selected_expiry,
            strike=float(strike),
            type=otype,
        )
        quote = self.data_service.get_quote(
            symbol, self.selected_expiry, float(strike), otype
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

    def update_chart(self) -> None:
        if self.strategy is None:
            return
        ivs: dict[tuple[float, OptionType], float] = {}
        strikes_sel: list[float] = []
        badges: list[BadgeSpec] = []
        for leg in self.strategy.legs:
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
                    },
                )
            )
        m = self.aggregator.aggregate(
            self.strategy, spot=self.strategy.underlier.spot, ivs=ivs
        )
        self._logger.info(
            "Updated chart: net=%.2f, be=%s", m.net_debit_credit, m.break_evens
        )
        self.strike_ruler.set_selected_strikes(strikes_sel)
        self.strike_ruler.set_badges(badges)
        cd = ChartPresenter.prepare(
            m,
            strike_lines=strikes_sel,
            current_price=self.strategy.underlier.spot,
        )
        self.chart.set_chart_data(cd)

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
