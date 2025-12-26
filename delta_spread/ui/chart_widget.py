import logging
from typing import override

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
)
from PyQt6.QtWidgets import QSizePolicy, QWidget

from ..services.presenter import ChartData


class ChartWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setMinimumHeight(350)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._prices: list[float] = []
        self._pnls: list[float] = []
        self._x_min: float = 0.0
        self._x_max: float = 1.0
        self._y_min: float = -1.0
        self._y_max: float = 1.0
        self._strike_lines: list[float] = []
        self._current_price: float = 0.0

    def set_chart_data(self, data: ChartData) -> None:
        self._prices = data.prices
        self._pnls = data.pnls
        self._x_min = data.x_min
        self._x_max = data.x_max
        self._y_min = data.y_min
        self._y_max = data.y_max
        self._strike_lines = data.strike_lines
        self._current_price = data.current_price
        logging.getLogger(__name__).info(
            "ChartData set: prices=%d pnls=%d x=[%.2f, %.2f] y=[%.2f, %.2f] strikes=%d current=%.2f",
            len(self._prices),
            len(self._pnls),
            self._x_min,
            self._x_max,
            self._y_min,
            self._y_max,
            len(self._strike_lines),
            self._current_price,
        )
        self.update()

    @override
    def paintEvent(self, a0: QPaintEvent | None) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_background_and_grid(painter)
        self._draw_zero_line(painter)
        self._draw_bell_curve(painter)
        self._draw_profit_loss_curves(painter)
        self._draw_current_price(painter)
        self._draw_strike_lines(painter)
        self._draw_legend(painter)

    def _draw_background_and_grid(self, painter: QPainter) -> None:
        self._draw_background(painter)
        self._draw_grid_y(painter)
        self._draw_grid_x(painter)

    def _draw_background(self, painter: QPainter) -> None:
        painter.fillRect(self.rect(), QColor("#F4F7FB"))

    def _draw_grid_y(self, painter: QPainter) -> None:
        w = self.width()
        h = self.height()
        left_m = 50
        bottom_m = 30
        right_m = 20
        top_m = 20
        graph_h = h - bottom_m - top_m
        painter.setPen(QPen(QColor("#E0E0E0"), 1, Qt.PenStyle.SolidLine))
        y_steps = 10
        y_range_threshold = 250.0
        for i in range(y_steps + 1):
            y = top_m + (i * graph_h / y_steps)
            painter.drawLine(left_m, int(y), w - right_m, int(y))
            val = self._y_min + (i * (self._y_max - self._y_min) / y_steps)
            use_int = abs(self._y_max - self._y_min) >= y_range_threshold
            label = f"${val:,.0f}" if use_int else f"${val:,.2f}"
            painter.setPen(QColor("#666666"))
            painter.setFont(QFont("Arial", 8))
            painter.drawText(
                QRect(0, int(y) - 10, left_m - 5, 20),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                label,
            )
            painter.setPen(QColor("#E0E0E0"))

    def _draw_grid_x(self, painter: QPainter) -> None:
        w = self.width()
        h = self.height()
        left_m = 50
        bottom_m = 30
        right_m = 20
        top_m = 20
        graph_w = w - left_m - right_m
        painter.setPen(QPen(QColor("#E0E0E0"), 1, Qt.PenStyle.SolidLine))
        x_steps = 20
        for i in range(x_steps + 1):
            x = left_m + (i * graph_w / x_steps)
            painter.drawLine(int(x), top_m, int(x), h - bottom_m)
            if i % 2 == 0:
                val = self._x_min + (i * (self._x_max - self._x_min) / x_steps)
                painter.setPen(QColor("#666666"))
                painter.drawText(
                    QRect(int(x) - 30, h - bottom_m, 60, 20),
                    Qt.AlignmentFlag.AlignCenter,
                    f"{val:,.0f}",
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
        # Calculate zero line position based on actual Y-axis range
        if self._y_max == self._y_min:
            return  # Can't draw zero line if no range
        # Only draw if zero is within the visible range
        if self._y_min <= 0 <= self._y_max:
            zero_y = top_m + (self._y_max - 0) / (self._y_max - self._y_min) * graph_h
            painter.setPen(QPen(QColor("#000000"), 1))
            painter.drawLine(left_m, int(zero_y), w - right_m, int(zero_y))

    def _draw_bell_curve(self, painter: QPainter) -> None:
        # Bell curve removed - was decorative and not based on actual position data
        pass

    def _draw_profit_loss_curves(self, painter: QPainter) -> None:
        w = self.width()
        h = self.height()
        left_m = 50
        bottom_m = 30
        right_m = 20
        top_m = 20
        graph_w = w - left_m - right_m
        graph_h = h - bottom_m - top_m
        if not self._prices or not self._pnls:
            return

        def map_x(px: float) -> float:
            if self._x_max == self._x_min:
                return float(left_m)
            return float(left_m) + (px - self._x_min) / (
                self._x_max - self._x_min
            ) * float(graph_w)

        def map_y(py: float) -> float:
            if self._y_max == self._y_min:
                return float(top_m)
            return float(top_m) + (self._y_max - py) / (
                self._y_max - self._y_min
            ) * float(graph_h)

        path = QPainterPath()
        path.moveTo(map_x(self._prices[0]), map_y(self._pnls[0]))
        for i in range(1, len(self._prices)):
            path.lineTo(map_x(self._prices[i]), map_y(self._pnls[i]))
        painter.setPen(QPen(QColor("#2E7D32"), 2))
        painter.drawPath(path)

    def _draw_current_price(self, painter: QPainter) -> None:
        w = self.width()
        h = self.height()
        left_m = 50
        bottom_m = 30
        right_m = 20
        top_m = 20
        graph_w = w - left_m - right_m
        if self._x_max == self._x_min:
            return
        px = float(left_m) + (self._current_price - self._x_min) / (
            self._x_max - self._x_min
        ) * float(graph_w)
        px_c = max(float(left_m), min(px, float(w - right_m)))
        painter.setPen(QPen(QColor("#2196F3"), 1))
        painter.drawLine(int(px_c), top_m, int(px_c), h - bottom_m)
        painter.setPen(QColor("#2196F3"))
        painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        painter.drawText(int(px_c) + 5, top_m + 20, f"{self._current_price:,.2f}")

    def _draw_strike_lines(self, painter: QPainter) -> None:
        w = self.width()
        h = self.height()
        left_m = 50
        bottom_m = 30
        right_m = 20
        top_m = 20
        graph_w = w - left_m - right_m
        if not self._strike_lines or self._x_max == self._x_min:
            return
        for s in self._strike_lines:
            px = float(left_m) + (s - self._x_min) / (
                self._x_max - self._x_min
            ) * float(graph_w)
            painter.setPen(QPen(QColor("#555"), 1, Qt.PenStyle.DotLine))
            painter.drawLine(int(px), top_m, int(px), h - bottom_m)

    @staticmethod
    def _draw_legend(painter: QPainter) -> None:
        left_m = 50
        top_m = 20
        legend_x = left_m + 10
        legend_y = top_m + 10
        row_h = 18
        items = [
            ("P&L at Expiration", Qt.PenStyle.SolidLine, QColor("#2E7D32")),
            ("Current Price", Qt.PenStyle.SolidLine, QColor("#2196F3")),
            ("Strike Price", Qt.PenStyle.DotLine, QColor("#555")),
        ]
        painter.setFont(QFont("Arial", 8))
        for idx, (text, style, color) in enumerate(items):
            y_pos = legend_y + (idx * row_h)
            painter.setPen(QPen(color, 2, style))
            painter.drawLine(legend_x, int(y_pos + 5), legend_x + 20, int(y_pos + 5))
            painter.setPen(QColor("#333"))
            painter.drawText(legend_x + 25, int(y_pos + 10), text)
