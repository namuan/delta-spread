from typing import TypedDict, override

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPaintEvent, QResizeEvent
from PyQt6.QtWidgets import QWidget

from .option_badge import OptionBadge
from .styles import COLOR_DANGER_RED, COLOR_GRAY_200, COLOR_TEXT_PRIMARY


class BadgeSpec(TypedDict):
    strike: float
    text: str
    color_bg: str
    placement: str


class StrikeRuler(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._strikes: list[float] = []
        self._selected: set[float] = set()
        self._badge_specs: list[BadgeSpec] = []
        self._badge_widgets: list[OptionBadge] = []

    def set_strikes(self, strikes: list[float]) -> None:
        self._strikes = strikes
        self.update()

    def set_selected_strikes(self, strikes: list[float]) -> None:
        self._selected = set(strikes)
        self.update()

    def set_badges(self, badges: list[BadgeSpec]) -> None:
        for w in self._badge_widgets:
            w.setParent(None)
            w.deleteLater()
        self._badge_widgets = []
        self._badge_specs = list(badges)
        for b in badges:
            pointer_up = b["placement"] == "bottom"
            w = OptionBadge(b["text"], b["color_bg"], pointer_up=pointer_up)
            w.setParent(self)
            self._badge_widgets.append(w)
        self._position_badges()

    @override
    def paintEvent(self, a0: QPaintEvent | None) -> None:
        p = QPainter(self)
        w = self.width()
        h = self.height()
        p.setPen(QColor(COLOR_GRAY_200))
        p.drawLine(0, h // 2, w, h // 2)
        if not self._strikes:
            return
        mn = min(self._strikes)
        mx = max(self._strikes)
        if mx == mn:
            mx = mn + 1
        p.setFont(QFont("Arial", 8))
        p.setPen(QColor(COLOR_TEXT_PRIMARY))
        for _i, s in enumerate(self._strikes):
            x = int((s - mn) / (mx - mn) * w)
            tick_h = 10
            color = (
                QColor(COLOR_DANGER_RED)
                if s in self._selected
                else QColor(COLOR_TEXT_PRIMARY)
            )
            p.setPen(color)
            p.drawLine(x, int(h // 2 - tick_h), x, int(h // 2 + tick_h))
            label = f"{s:.2f}".rstrip("0").rstrip(".")
            rect = QRect(int(x) - 22, int(h // 2 - 24), 44, 16)
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)
        self._position_badges(mn, mx)

    def _position_badges(
        self, mn: float | None = None, mx: float | None = None
    ) -> None:
        if not self._badge_widgets:
            return
        if not self._strikes:
            for w in self._badge_widgets:
                w.hide()
            return
        w_width = self.width()
        h_height = self.height()
        if mn is None:
            mn = min(self._strikes)
        if mx is None:
            mx = max(self._strikes)
        if mx == mn:
            for w in self._badge_widgets:
                w.hide()
            return
        top_y = 0
        bottom_y = max(0, h_height - 25 - 6)
        buckets: dict[int, int] = {}
        for idx, spec in enumerate(self._badge_specs):
            x = int((spec["strike"] - mn) / (mx - mn) * w_width)
            b = round(x / 10)
            c = buckets.get(b, 0) + 1
            buckets[b] = c
            delta = 12 * c * (-1 if c % 2 else 1)
            x_adj = max(
                0,
                min(
                    w_width - self._badge_widgets[idx].width(),
                    x + delta - self._badge_widgets[idx].width() // 2,
                ),
            )
            self._badge_widgets[idx].move(
                x_adj, top_y if spec["placement"] == "top" else bottom_y
            )
            self._badge_widgets[idx].show()

    @override
    def resizeEvent(self, a0: QResizeEvent | None) -> None:
        self._position_badges()
        super().resizeEvent(a0)
