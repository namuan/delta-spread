from typing import override

from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPaintEvent
from PyQt6.QtWidgets import QWidget


class StrikeRuler(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._strikes: list[float] = []
        self._selected: set[float] = set()

    def set_strikes(self, strikes: list[float]) -> None:
        self._strikes = strikes
        self.update()

    def set_selected_strikes(self, strikes: list[float]) -> None:
        self._selected = set(strikes)
        self.update()

    @override
    def paintEvent(self, a0: QPaintEvent | None) -> None:
        p = QPainter(self)
        w = self.width()
        h = self.height()
        p.setPen(QColor("#DDD"))
        p.drawLine(0, h // 2, w, h // 2)
        if not self._strikes:
            return
        mn = min(self._strikes)
        mx = max(self._strikes)
        if mx == mn:
            mx = mn + 1
        p.setFont(QFont("Arial", 8))
        p.setPen(QColor("#333"))
        for _i, s in enumerate(self._strikes):
            x = int((s - mn) / (mx - mn) * w)
            tick_h = 10
            color = QColor("#DC2626") if s in self._selected else QColor("#333")
            p.setPen(color)
            p.drawLine(x, int(h // 2 - tick_h), x, int(h // 2 + tick_h))
            label = f"{s:.2f}".rstrip("0").rstrip(".")
            rect = QRect(int(x) - 22, int(h // 2 - 24), 44, 16)
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)
