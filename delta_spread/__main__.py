from datetime import date
import sys

from PyQt6.QtCore import QPointF, QRect, Qt
from PyQt6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
    QPolygonF,
)
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from .options_data_mock import MockOptionsDataService


class ChartWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(350)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def paintEvent(self, _event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_background_and_grid(painter)
        self._draw_zero_line(painter)
        self._draw_bell_curve(painter)
        self._draw_profit_loss_curves(painter)
        self._draw_current_price(painter)
        self._draw_strike_line(painter)
        self._draw_legend(painter)

    def _draw_background_and_grid(self, painter: QPainter) -> None:
        w = self.width()
        h = self.height()
        left_m = 50
        bottom_m = 30
        right_m = 20
        top_m = 20
        graph_w = w - left_m - right_m
        graph_h = h - bottom_m - top_m
        painter.fillRect(self.rect(), QColor("#F4F7FB"))
        painter.setPen(QPen(QColor("#E0E0E0"), 1, Qt.PenStyle.SolidLine))
        y_steps = 10
        for i in range(y_steps + 1):
            y = top_m + (i * graph_h / y_steps)
            painter.drawLine(left_m, int(y), w - right_m, int(y))
            val = 6000 - (i * 1000)
            label = f"${val:,}" if val != 0 else "$0"
            painter.setPen(QColor("#666666"))
            painter.setFont(QFont("Arial", 8))
            painter.drawText(
                QRect(0, int(y) - 10, left_m - 5, 20),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                label,
            )
            painter.setPen(QColor("#E0E0E0"))
        x_steps = 20
        for i in range(x_steps + 1):
            x = left_m + (i * graph_w / x_steps)
            painter.drawLine(int(x), top_m, int(x), h - bottom_m)
            if i % 2 == 0:
                val = 6380 + (i * 25)
                painter.setPen(QColor("#666666"))
                painter.drawText(
                    QRect(int(x) - 20, h - bottom_m, 40, 20),
                    Qt.AlignmentFlag.AlignCenter,
                    str(val),
                )
                painter.setPen(QColor("#E0E0E0"))

    def _draw_zero_line(self, painter: QPainter) -> None:
        w = self.width()
        h = self.height()
        left_m = 50
        bottom_m = 30
        right_m = 20
        top_m = 20
        graph_h = h - bottom_m - top_m
        zero_y = top_m + (6 * graph_h / 10)
        painter.setPen(QPen(QColor("#000000"), 1))
        painter.drawLine(left_m, int(zero_y), w - right_m, int(zero_y))

    def _draw_bell_curve(self, painter: QPainter) -> None:
        w = self.width()
        h = self.height()
        left_m = 50
        bottom_m = 30
        right_m = 20
        top_m = 20
        graph_w = w - left_m - right_m
        center_x = left_m + (graph_w * 0.55)
        path_bell = QPainterPath()
        path_bell.moveTo(left_m + (graph_w * 0.2), h - bottom_m)
        path_bell.cubicTo(
            center_x - 100,
            h - bottom_m,
            center_x - 50,
            top_m + 100,
            center_x,
            top_m + 100,
        )
        path_bell.cubicTo(
            center_x + 50,
            top_m + 100,
            center_x + 100,
            h - bottom_m,
            left_m + (graph_w * 0.8),
            h - bottom_m,
        )
        grad = QLinearGradient(center_x, top_m, center_x, h - bottom_m)
        grad.setColorAt(0, QColor(100, 180, 255, 100))
        grad.setColorAt(1, QColor(100, 180, 255, 0))
        painter.fillPath(path_bell, grad)

    def _draw_profit_loss_curves(self, painter: QPainter) -> None:
        w = self.width()
        h = self.height()
        left_m = 50
        bottom_m = 30
        right_m = 20
        top_m = 20
        graph_w = w - left_m - right_m
        graph_h = h - bottom_m - top_m
        center_x = left_m + (graph_w * 0.55)
        zero_y = top_m + (6 * graph_h / 10)
        painter.setPen(QPen(QColor("#66BB6A"), 2, Qt.PenStyle.DashLine))
        path_green_dash = QPainterPath()
        path_green_dash.moveTo(left_m, zero_y + 20)
        path_green_dash.quadTo(center_x, top_m + 50, w - right_m, zero_y + 50)
        painter.drawPath(path_green_dash)
        path_solid = QPainterPath()
        path_solid.moveTo(left_m, zero_y + 10)
        peak_x = center_x - 40
        peak_y = zero_y - 30
        path_solid.quadTo(peak_x, peak_y - 10, center_x, peak_y + 5)
        path_solid.lineTo(w - right_m, zero_y + 150)
        painter.setPen(QPen(QColor("#2E7D32"), 2))
        painter.drawPath(path_solid)
        painter.setPen(QPen(QColor("#EF5350"), 2, Qt.PenStyle.DotLine))
        path_red_dash = QPainterPath()
        path_red_dash.moveTo(left_m, zero_y + 40)
        path_red_dash.quadTo(
            center_x - 20, zero_y - 100, w - right_m, h - bottom_m + 50
        )
        painter.drawPath(path_red_dash)

    def _draw_current_price(self, painter: QPainter) -> None:
        w = self.width()
        h = self.height()
        left_m = 50
        bottom_m = 30
        right_m = 20
        top_m = 20
        graph_w = w - left_m - right_m
        center_x = left_m + (graph_w * 0.55)
        price_x = center_x + 10
        painter.setPen(QPen(QColor("#2196F3"), 1))
        painter.drawLine(int(price_x), top_m, int(price_x), h - bottom_m)
        painter.setPen(QColor("#2196F3"))
        painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        painter.drawText(int(price_x) + 5, top_m + 20, "6,610.20")

    def _draw_strike_line(self, painter: QPainter) -> None:
        w = self.width()
        h = self.height()
        left_m = 50
        bottom_m = 30
        right_m = 20
        top_m = 20
        graph_w = w - left_m - right_m
        center_x = left_m + (graph_w * 0.55)
        painter.setPen(QPen(QColor("#555"), 1, Qt.PenStyle.DotLine))
        painter.drawLine(int(center_x - 40), top_m, int(center_x - 40), h - bottom_m)

    @staticmethod
    def _draw_legend(painter: QPainter) -> None:
        left_m = 50
        top_m = 20
        legend_x = left_m + 10
        legend_y = top_m + 10
        row_h = 18
        items = [
            ("Sat Nov 22nd (now)", Qt.PenStyle.SolidLine, QColor("#333")),
            ("Tue Dec 2nd (10d)", Qt.PenStyle.DashLine, QColor("#555")),
            ("Expiration (14d)", Qt.PenStyle.DotLine, QColor("#777")),
        ]
        painter.setFont(QFont("Arial", 8))
        for idx, (text, style, color) in enumerate(items):
            y_pos = legend_y + (idx * row_h)
            painter.setPen(QPen(color, 2, style))
            painter.drawLine(legend_x, int(y_pos + 5), legend_x + 20, int(y_pos + 5))
            painter.setPen(QColor("#333"))
            painter.drawText(legend_x + 25, int(y_pos + 10), text)
        y_pos = legend_y + (3 * row_h)
        painter.setBrush(QColor(100, 180, 255, 100))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(
            QPolygonF([
                QPointF(legend_x, y_pos + 10),
                QPointF(legend_x + 10, y_pos),
                QPointF(legend_x + 20, y_pos + 10),
            ]).toPolygon()
        )
        painter.setPen(QColor("#333"))
        painter.drawText(legend_x + 25, int(y_pos + 10), "Probability")


class OptionBadge(QWidget):
    def __init__(self, text: str, color_bg: str, *, is_call: bool = False) -> None:
        super().__init__()
        self.text = text
        self.color_bg = color_bg
        self.is_call = is_call
        self.setFixedSize(50, 25)

    def paintEvent(self, _event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Flag shape
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height() - 5, 3, 3)

        # Triangle at bottom
        path.moveTo(self.width() / 2 - 5, self.height() - 5)
        path.lineTo(self.width() / 2, self.height())
        path.lineTo(self.width() / 2 + 5, self.height() - 5)

        painter.fillPath(path, QColor(self.color_bg))

        painter.setPen(Qt.GlobalColor.white)
        painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        painter.drawText(
            self.rect().adjusted(0, 0, 0, -5), Qt.AlignmentFlag.AlignCenter, self.text
        )


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Diagonal Put Spread Analyzer")
        self.resize(1200, 850)

        self.data_service = MockOptionsDataService()
        self.expiries: list[date] = []
        self.selected_expiry: date | None = None

        # Main Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setSpacing(5)
        self.main_layout.setContentsMargins(10, 10, 10, 10)

        # Background color
        self.setStyleSheet(
            "background-color: #FFFFFF; color: #333333; font-family: 'Segoe UI', Arial;"
        )

        self.setup_header()
        self.setup_instrument_info()
        self.setup_timeline()
        self.setup_strikes()
        self.setup_metrics()
        self.setup_chart()
        self.setup_footer_controls()
        self.setup_bottom_tabs()

        self.on_symbol_changed()

    def setup_header(self) -> None:
        header_layout = QHBoxLayout()

        # Title
        title = QLabel("Diagonal Put Spread")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #222;")
        help_icon = QLabel("?")
        help_icon.setStyleSheet(
            "border: 1px solid #AAA; border-radius: 9px; min-width: 18px; min-height: 18px; qproperty-alignment: AlignCenter; color: #555;"
        )

        header_layout.addWidget(title)
        header_layout.addWidget(help_icon)
        header_layout.addStretch()

        # Buttons
        btn_style = """
            QPushButton {
                background-color: #3B82F6;
                color: white;
                border-radius: 4px;
                padding: 5px 10px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2563EB; }
        """

        btn_add = QPushButton("Add +")
        btn_pos = QPushButton("Positions (2)")
        btn_save = QPushButton("Save Trade")
        btn_hist = QPushButton("Historical Chart")

        for btn in [btn_add, btn_pos, btn_save, btn_hist]:
            btn.setStyleSheet(btn_style)
            header_layout.addWidget(btn)

        self.main_layout.addLayout(header_layout)

    def setup_instrument_info(self) -> None:
        info_layout = QHBoxLayout()
        info_layout.setContentsMargins(0, 10, 0, 10)

        self.symbol_input = QLineEdit("SPX")
        self.symbol_input.setFixedWidth(60)
        self.symbol_input.setStyleSheet(
            "border: 1px solid #CCC; border-radius: 3px; padding: 3px; font-weight: bold;"
        )
        self.symbol_input.returnPressed.connect(self.on_symbol_changed)
        self.symbol_input.editingFinished.connect(self.on_symbol_changed)

        price_label = QLabel("6,602.99")
        price_label.setStyleSheet("font-size: 16px; font-weight: bold;")

        change_label = QLabel("+0.98%\n+64.23")
        change_label.setStyleSheet(
            "color: #22C55E; font-size: 11px; font-weight: bold;"
        )

        realtime_label = QLabel("Real-time")
        realtime_label.setStyleSheet("color: #888;")
        rt_help = QLabel("?")
        rt_help.setStyleSheet(
            "border: 1px solid #AAA; border-radius: 7px; min-width: 14px; min-height: 14px; qproperty-alignment: AlignCenter; font-size: 10px; color: #555;"
        )

        info_layout.addWidget(self.symbol_input)
        info_layout.addSpacing(10)
        info_layout.addWidget(price_label)
        info_layout.addSpacing(10)
        info_layout.addWidget(change_label)
        info_layout.addSpacing(15)
        info_layout.addWidget(realtime_label)
        info_layout.addWidget(rt_help)
        info_layout.addStretch()

        self.main_layout.addLayout(info_layout)

        self.exp_label = QLabel("EXPIRATIONS:")
        self.exp_label.setStyleSheet("font-size: 12px;")
        self.main_layout.addWidget(self.exp_label)

    def setup_timeline(self) -> None:
        self.timeline_frame = QFrame()
        self.timeline_frame.setStyleSheet(
            "background-color: #EAEAEA; border-radius: 3px;"
        )
        self.timeline_layout = QVBoxLayout(self.timeline_frame)
        self.timeline_layout.setContentsMargins(0, 0, 0, 0)
        self.timeline_layout.setSpacing(0)

        self.month_layout = QHBoxLayout()
        self.month_layout.setContentsMargins(10, 2, 10, 2)
        self.timeline_layout.addLayout(self.month_layout)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("color: #BBB;")
        self.timeline_layout.addWidget(line)

        self.days_layout = QHBoxLayout()
        self.days_layout.setContentsMargins(5, 2, 5, 2)
        self.days_layout.setSpacing(15)
        self.timeline_layout.addLayout(self.days_layout)

        self.main_layout.addWidget(self.timeline_frame)

    def on_symbol_changed(self) -> None:
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
            lbl.setStyleSheet("color: #555; font-weight: bold; font-size: 12px;")
            self.month_layout.addWidget(lbl)
            self.month_layout.addStretch()
        self.expiry_buttons: dict[date, QPushButton] = {}
        for d in self.expiries:
            btn = QPushButton(d.strftime("%d"))
            btn.setStyleSheet("color: #333; font-size: 11px; font-weight: bold;")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _=False, dd=d: self.on_expiry_selected(dd))
            self.days_layout.addWidget(btn)
            self.expiry_buttons[d] = btn
        self.days_layout.addStretch()

    def on_expiry_selected(self, d: date) -> None:
        self.selected_expiry = d
        for ed, btn in self.expiry_buttons.items():
            if ed == d:
                btn.setStyleSheet(
                    "background-color: #5CACEE; color: white; border-radius: 2px; padding: 2px 5px;"
                )
            else:
                btn.setStyleSheet("color: #333; font-size: 11px; font-weight: bold;")

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
        # Container for the strikes ruler visualization
        container = QWidget()
        container.setFixedHeight(60)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        # Top label
        lbl = QLabel("STRIKES:")
        lbl.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(lbl)

        # Ruler area (using a layout for simulated tick marks and badges)
        ruler_layout = QHBoxLayout()
        ruler_layout.setContentsMargins(20, 0, 20, 0)
        ruler_layout.setSpacing(0)

        # Just simulating the ruler look with a custom widget approach would be hard
        # without drawing. Let's use a QFrame with a custom paint for ticks.

        class StrikeRuler(QWidget):
            def paintEvent(self, _event: QPaintEvent) -> None:
                p = QPainter(self)
                w = self.width()
                h = self.height()

                # Draw center line
                p.setPen(QColor("#DDD"))
                p.drawLine(0, h // 2, w, h // 2)

                # Draw ticks
                p.setFont(QFont("Arial", 8))
                p.setPen(QColor("#888"))

                step = w / 30
                for i in range(31):
                    x = i * step
                    is_major = i % 5 == 0
                    tick_h = 10 if is_major else 5
                    p.drawLine(
                        int(x), int(h // 2 - tick_h), int(x), int(h // 2 + tick_h)
                    )

                    if is_major:
                        # Number
                        val = 6375 + (i * 25)  # Mock values
                        rect = QRect(int(x) - 15, int(h // 2 + 12), 30, 15)
                        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(val))

        ruler = StrikeRuler()
        ruler.setFixedHeight(40)

        # Overlay Badges (Using absolute positioning relative to the ruler container)
        # We can't easily mix absolute widgets inside a layout, so we'll add them to the ruler widget
        # but since we are just creating the UI, let's add them to a layout on top of the ruler?
        # Easier: Add them to ruler widget as children

        # Badge 1
        b1 = OptionBadge("6580P", "#D32F2F")
        b1.setParent(ruler)
        b1.move(450, 0)  # Approx px position
        lbl_date1 = QLabel("12/5", ruler)
        lbl_date1.setStyleSheet(
            "background-color: #5CACEE; color: white; font-size: 9px; padding: 1px; border-radius: 2px;"
        )
        lbl_date1.move(465, 26)

        # Badge 2 (Current Price/SPX Marker)
        spx_mark = QLabel("SPX", ruler)
        spx_mark.setStyleSheet("font-size: 9px; font-weight: bold; color: #333;")
        spx_mark.move(535, 5)
        tri = QLabel("▼", ruler)
        tri.setStyleSheet("color: #333; font-size: 10px;")
        tri.move(540, 15)

        # Badge 3
        b2 = OptionBadge("6630P", "#AA00FF")
        b2.setParent(ruler)
        b2.move(600, 0)
        lbl_date2 = QLabel("12/19", ruler)
        lbl_date2.setStyleSheet(
            "background-color: #AA00FF; color: white; font-size: 9px; padding: 1px; border-radius: 2px;"
        )
        lbl_date2.move(610, -12)  # Above

        layout.addWidget(ruler)
        self.main_layout.addWidget(container)

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
            t_lbl.setStyleSheet("color: #666; font-size: 10px; font-weight: bold;")

            val_layout = QHBoxLayout()
            if icon_char:
                icon = QLabel(icon_char)
                icon.setStyleSheet("font-size: 12px;")
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
                s_lbl.setStyleSheet("color: #666; font-size: 10px;")
                v_layout.addWidget(s_lbl)

            # Alignment wrapper
            container = QWidget()
            container.setLayout(v_layout)
            return container

        # Net Debit
        m1 = create_metric("NET DEBIT:", "$5,850", "#000", "🪙")

        # Max Loss
        m2 = create_metric("MAX LOSS:", "$5,850", "#000", "↘")
        # Red arrow overlay simulation

        # Max Profit
        m3 = create_metric("MAX PROFIT:", "$5,841.72", "#22C55E", "↗")

        # Chance of Profit
        m4 = create_metric("CHANCE OF PROFIT:", "49%", "#000", "🎲")

        # Breakevens
        m5 = create_metric("BREAKEVENS:", "Between 6,382.88 - 6,709.99", "#000", "→")

        layout.addWidget(m1)
        layout.addWidget(m2)
        layout.addWidget(m3)
        layout.addWidget(m4)
        layout.addWidget(m5)
        layout.addStretch()

        self.main_layout.addWidget(metrics_frame)

    def setup_chart(self) -> None:
        # Arrows for side scrolling
        chart_layout = QHBoxLayout()
        left_arrow = QLabel("<")
        left_arrow.setStyleSheet("color: #CCC; font-size: 20px;")

        self.chart = ChartWidget()

        right_arrow = QLabel(">")
        right_arrow.setStyleSheet("color: #CCC; font-size: 20px;")

        chart_layout.addWidget(left_arrow)
        chart_layout.addWidget(self.chart)
        chart_layout.addWidget(right_arrow)

        self.main_layout.addLayout(chart_layout)

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
        lbl_refresh.setStyleSheet(
            "background: #CCC; border-radius: 8px; color: white; padding: 2px;"
        )
        row.addWidget(lbl_range)
        row.addStretch()
        row.addWidget(lbl_refresh)
        iv_widget = QWidget()
        iv_layout = QHBoxLayout(iv_widget)
        iv_layout.setContentsMargins(0, 0, 0, 0)
        btn_avg = QPushButton("AVERAGE ▼")
        btn_avg.setStyleSheet(
            "background: #777; color: white; border: none; padding: 4px 8px; border-radius: 3px; font-size: 10px; font-weight: bold;"
        )
        lbl_iv = QLabel("IMPLIED VOLATILITY: <b>18.8%</b>")
        lbl_iv.setStyleSheet("font-size: 11px;")
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
            m.setStyleSheet("color: #888; font-size: 9px;")
        markers.addWidget(m1)
        markers.addStretch()
        markers.addWidget(m2)
        markers.addStretch()
        markers.addWidget(m3)
        return markers

    @staticmethod
    def _build_date_slider() -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setStyleSheet(
            """
            QSlider::groove:horizontal { height: 6px; background: #DDD; border-radius: 3px; }
            QSlider::handle:horizontal { background: #888; width: 12px; margin: -3px 0; border-radius: 6px; }
            """
        )
        return slider

    @staticmethod
    def _build_range_slider() -> QSlider:
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setValue(30)
        slider.setStyleSheet(
            """
            QSlider::groove:horizontal { height: 4px; background: #DDD; border-radius: 2px; }
            QSlider::handle:horizontal { background: #5CACEE; width: 6px; height: 15px; margin: -6px 0; border-radius: 0px; }
            QSlider::sub-page:horizontal { background: #5CACEE; }
            """
        )
        return slider

    def setup_bottom_tabs(self) -> None:
        tab_layout = QHBoxLayout()
        tab_layout.setSpacing(0)

        buttons = [
            ("Table", False),
            ("Graph", True),
            ("Profit / Loss $", True),
            ("Profit / Loss %", False),
            ("Contract Value", False),
            ("% of Max Risk", False),
            ("More", False),
        ]

        for text, is_active in buttons:
            btn = QPushButton(text)

            if "Table" in text:
                btn.setIcon(QIcon.fromTheme("view-list-details"))  # Placeholder logic
                # Text prefix icon simulation
                btn.setText(" 田 " + text)
            elif "Graph" in text:
                btn.setText(" 📈 " + text)
            elif "More" in text:
                btn.setText("▼ " + text)

            if is_active:
                if text == "Graph":
                    # Blue active
                    style = "background-color: #5CACEE; color: white; border: 1px solid #5CACEE;"
                elif text == "Profit / Loss $":
                    # Light blue active
                    style = "background-color: #5CACEE; color: white; border: 1px solid #5CACEE;"
                else:
                    style = (
                        "background-color: white; color: #333; border: 1px solid #CCC;"
                    )
            else:
                style = "background-color: white; color: #333; border: 1px solid #CCC;"

            btn.setStyleSheet(f"""
                QPushButton {{
                    {style}
                    padding: 8px;
                    font-size: 12px;
                    font-weight: bold;
                }}
            """)
            tab_layout.addWidget(btn)

        self.main_layout.addLayout(tab_layout)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Font Setup to look cleaner
    font = QFont("Segoe UI", 9)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
