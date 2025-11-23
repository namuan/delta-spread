from collections.abc import Callable
from typing import TypedDict, override

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import (
    QColor,
    QFont,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QResizeEvent,
    QWheelEvent,
)
from PyQt6.QtWidgets import QWidget

from ..domain.models import OptionType
from .option_badge import OptionBadge
from .styles import (
    COLOR_DANGER_RED,
    COLOR_GRAY_200,
    COLOR_TEXT_PRIMARY,
)


class BadgeSpec(TypedDict):
    strike: float
    text: str
    color_bg: str
    placement: str
    leg_idx: int


class StrikeRuler(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._strikes: list[float] = []
        self._selected: set[float] = set()
        self._badge_specs: list[BadgeSpec] = []
        self._badge_widgets: list[OptionBadge] = []
        self._scroll_x: int = 0
        self._drag_active: bool = False
        self._drag_last_x: int = 0
        self._pixel_step: int = 40
        self._current_price: float | None = None
        self._current_label: str | None = None
        self._center_strike: float | None = None
        self._toggle_handler: Callable[[int, OptionType], None] | None = None

    def set_toggle_handler(
        self, handler: Callable[[int, OptionType], None] | None
    ) -> None:
        self._toggle_handler = handler

    def set_strikes(self, strikes: list[float]) -> None:
        self._strikes = strikes
        self.update()
        self._update_center_strike()

    def set_current_price(self, price: float, label: str | None = None) -> None:
        self._current_price = price
        self._current_label = label
        self.update()

    def center_on_value(self, value: float) -> None:
        if not self._strikes:
            return
        idx = self._nearest_index(value)
        content = self._content_width()
        centre_x = self.width() // 2
        self._scroll_x = max(
            0, min(idx * self._pixel_step - centre_x, max(0, content - self.width()))
        )
        self.update()
        self._position_badges()
        self._update_center_strike()

    def set_selected_strikes(self, strikes: list[float]) -> None:
        self._selected = set(strikes)
        self.update()

    def get_center_strike(self) -> float | None:
        return self._center_strike

    def get_current_price(self) -> float | None:
        return self._current_price

    def set_badges(self, badges: list[BadgeSpec]) -> None:
        for w in self._badge_widgets:
            w.setParent(None)
            w.deleteLater()
        self._badge_widgets = []
        self._badge_specs = list(badges)
        for b in badges:
            pointer_up = b["placement"] == "bottom"
            w = OptionBadge(b["text"], b["color_bg"], pointer_up=pointer_up)
            if self._toggle_handler is not None:
                w.set_toggle_context(b["leg_idx"], self._toggle_handler)
            w.setParent(self)
            self._badge_widgets.append(w)
        self._position_badges()

    @override
    def paintEvent(self, a0: QPaintEvent | None) -> None:
        p = QPainter(self)
        w = self.width()
        h = self.height()
        self._draw_baseline(p, w, h)
        if not self._strikes:
            return
        self._draw_strike_ticks(p, w, h)
        self._draw_current_price_indicator(p, w)
        self._position_badges()

    @staticmethod
    def _draw_baseline(p: QPainter, w: int, h: int) -> None:
        p.setPen(QColor(COLOR_GRAY_200))
        p.drawLine(0, h // 2, w, h // 2)

    def _draw_strike_ticks(self, p: QPainter, w: int, h: int) -> None:
        p.setFont(QFont("Arial", 8))
        margin = 50
        for i, s in enumerate(self._strikes):
            x = i * self._pixel_step - self._scroll_x
            if x < -margin or x > w + margin:
                continue
            tick_h_top = 10
            tick_h_bottom = 10
            color = QColor(COLOR_TEXT_PRIMARY)
            p.setPen(color)
            if self._center_strike is not None and s == self._center_strike:
                p.setBrush(color)
                p.drawEllipse(int(x) - 3, int(h // 2) - 3, 6, 6)
            elif s in self._selected:
                tick_h_top = 12
                tick_h_bottom = 12
            p.drawLine(int(x), int(h // 2 - tick_h_top), int(x), int(h // 2))
            p.drawLine(int(x), int(h // 2), int(x), int(h // 2 + tick_h_bottom))
            label = f"{s:.2f}".rstrip("0").rstrip(".")
            rect = QRect(int(x) - 22, int(h // 2 - 24), 44, 16)
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

    def _draw_current_price_indicator(self, p: QPainter, w: int) -> None:
        if self._current_price is None:
            return
        margin = 50
        x_price = self._compute_price_x(self._current_price)
        if x_price is None:
            return
        if -margin <= x_price <= w + margin:
            p.setPen(QColor(COLOR_DANGER_RED))
            txt = (
                f"{self._current_label}".strip()
                if self._current_label is not None
                else f"{self._current_price:.2f}"
            )
            rect = QRect(int(x_price) - 35, 2, 70, 16)
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, txt)

    def _compute_price_x(self, price: float) -> float | None:
        if not self._strikes:
            return None
        idx = self._nearest_index(price)
        if idx <= 0:
            x_base = 0
            frac = 0.0
        elif idx >= len(self._strikes) - 1:
            x_base = (len(self._strikes) - 1) * self._pixel_step
            frac = 0.0
        else:
            s0 = self._strikes[idx]
            if price >= s0:
                s1 = self._strikes[idx + 1]
                step = max(1e-9, s1 - s0)
                frac = max(0.0, min(1.0, (price - s0) / step))
                x_base = idx * self._pixel_step
            else:
                s1 = self._strikes[idx - 1]
                step = max(1e-9, s0 - s1)
                frac = max(0.0, min(1.0, (price - s1) / step))
                x_base = (idx - 1) * self._pixel_step
        return x_base + frac * self._pixel_step - self._scroll_x

    def _position_badges(self) -> None:
        if not self._badge_widgets:
            return
        if not self._strikes:
            for w in self._badge_widgets:
                w.hide()
            return
        w_width = self.width()
        h_height = self.height()
        top_y = 0
        bottom_y = max(0, h_height - 25 - 6)
        for idx, spec in enumerate(self._badge_specs):
            si = self._nearest_index(spec["strike"])
            x = si * self._pixel_step - self._scroll_x
            x_adj = max(
                0,
                min(
                    w_width - self._badge_widgets[idx].width(),
                    x - self._badge_widgets[idx].width() // 2,
                ),
            )
            self._badge_widgets[idx].move(
                x_adj, top_y if spec["placement"] == "top" else bottom_y
            )
            self._badge_widgets[idx].show()

    @override
    def resizeEvent(self, a0: QResizeEvent | None) -> None:
        self._position_badges()
        self._update_center_strike()
        super().resizeEvent(a0)

    def _nearest_index(self, value: float) -> int:
        if not self._strikes:
            return 0
        return min(
            range(len(self._strikes)), key=lambda i: abs(self._strikes[i] - value)
        )

    def _content_width(self) -> int:
        return len(self._strikes) * self._pixel_step

    @override
    def mousePressEvent(self, a0: QMouseEvent | None) -> None:
        if a0 is None:
            return
        if a0.button() == Qt.MouseButton.LeftButton:
            self._drag_active = True
            self._drag_last_x = int(a0.position().x())
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(a0)

    @override
    def mouseMoveEvent(self, a0: QMouseEvent | None) -> None:
        if a0 is None:
            return
        if self._drag_active:
            x = int(a0.position().x())
            dx = x - self._drag_last_x
            self._drag_last_x = x
            self._scroll_x = max(
                0,
                min(self._scroll_x - dx, max(0, self._content_width() - self.width())),
            )
            self.update()
            self._position_badges()
            self._update_center_strike()
        super().mouseMoveEvent(a0)

    @override
    def mouseReleaseEvent(self, a0: QMouseEvent | None) -> None:
        if a0 is None:
            return
        if a0.button() == Qt.MouseButton.LeftButton:
            self._drag_active = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(a0)

    @override
    def wheelEvent(self, a0: QWheelEvent | None) -> None:
        if a0 is None:
            return
        pd = a0.pixelDelta()
        ad = a0.angleDelta()
        dx = pd.x() if not pd.isNull() else ad.x()
        if dx == 0:
            dx = ad.y()
        if dx != 0:
            self._scroll_x = max(
                0,
                min(
                    self._scroll_x - dx,
                    max(0, self._content_width() - self.width()),
                ),
            )
            self.update()
            self._position_badges()
            self._update_center_strike()
            a0.accept()
        else:
            super().wheelEvent(a0)

    def _update_center_strike(self) -> None:
        if not self._strikes:
            self._center_strike = None
            return
        centre_x = self._scroll_x + (self.width() // 2)
        idx = max(0, min(len(self._strikes) - 1, round(centre_x / self._pixel_step)))
        self._center_strike = self._strikes[idx]
