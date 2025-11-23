from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..services.options_data_mock import MockOptionsDataService
from .chart_widget import ChartWidget
from .menus.add_menu import build_add_menu
from .strike_ruler import StrikeRuler
from .styles import (
    APP_STYLE,
    AVERAGE_BUTTON_STYLE,
    BUTTON_PRIMARY_STYLE,
    CHANGE_LABEL_STYLE,
    CHART_ARROW_STYLE,
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
    from ..services.options_data import OptionsDataService


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Delta Spread - Collapse the wave function of uncertainty")
        self.resize(1200, 850)
        self.data_service: OptionsDataService = MockOptionsDataService()
        self.expiries: list[date] = []
        self.selected_expiry: date | None = None
        self.strikes: list[float] = []
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
        self.symbol_input.returnPressed.connect(self.on_symbol_changed)
        self.symbol_input.editingFinished.connect(self.on_symbol_changed)
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
        self.btn_add.clicked.connect(self.show_add_menu)
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
        months = []
        for d in self.expiries:
            m = d.strftime("%b")
            if m not in months:
                months.append(m)
        for m in months:
            lbl = QLabel(m)
            lbl.setStyleSheet(MONTH_LABEL_STYLE)
            self.month_layout.addWidget(lbl)
            self.month_layout.addStretch()
        self.expiry_buttons: dict[date, QPushButton] = {}
        for d in self.expiries:
            btn = QPushButton(d.strftime("%d"))
            btn.setStyleSheet(DAY_BTN_STYLE)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, dd=d: self.on_expiry_selected(dd))
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
    def _clear_layout(layout: QHBoxLayout | QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
            child = item.layout()
            if child is not None:
                MainWindow._clear_layout(child)

    def setup_strikes(self) -> None:
        container = QWidget()
        container.setFixedHeight(60)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("STRIKES:")
        lbl.setStyleSheet(MONTH_LABEL_STYLE)
        layout.addWidget(lbl)
        self.strike_ruler = StrikeRuler()
        self.strike_ruler.setFixedHeight(40)
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
        ) -> QWidget:
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
            return container

        m1 = create_metric("NET DEBIT:", "$5,850", "#000", "🪙")
        m2 = create_metric("MAX LOSS:", "$5,850", "#000", "↘")
        m3 = create_metric("MAX PROFIT:", "$5,841.72", "#22C55E", "↗")
        m4 = create_metric("CHANCE OF PROFIT:", "49%", "#000", "🎲")
        m5 = create_metric("BREAKEVENS:", "Between 6,382.88 - 6,709.99", "#000", "→")
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
        self.add_menu.exec(p)

    def on_add_option(self, key: str) -> None:
        pass

    def setup_footer_controls(self) -> None:
        controls_layout = QVBoxLayout()
        controls_layout.addLayout(self._build_date_row())
        controls_layout.addWidget(self._build_date_slider())
        controls_layout.addLayout(self._build_iv_row())
        controls_layout.addWidget(self._build_range_slider())
        controls_layout.addLayout(self._build_markers_layout())
        self.main_layout.addLayout(controls_layout)

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
