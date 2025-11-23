from datetime import date
from typing import TYPE_CHECKING, cast

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .styles import (
    DAY_BTN_SELECTED_STYLE,
    DAY_BTN_STYLE,
    HLINE_STYLE,
    MONTH_LABEL_STYLE,
    TIMELINE_FRAME_STYLE,
)

if TYPE_CHECKING:
    from collections.abc import Callable as TCallable


class TimelineWidget(QWidget):
    expiry_selected = pyqtSignal(date)

    def __init__(self) -> None:
        super().__init__()
        self.expiries: list[date] = []
        self.expiry_buttons: dict[date, QPushButton] = {}
        self.frame = QFrame()
        self.frame.setStyleSheet(TIMELINE_FRAME_STYLE)
        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)
        self.frame_layout = QVBoxLayout(self.frame)
        self.frame_layout.setContentsMargins(0, 0, 0, 0)
        self.frame_layout.setSpacing(0)
        self.month_layout = QHBoxLayout()
        self.month_layout.setContentsMargins(10, 2, 10, 2)
        self.frame_layout.addLayout(self.month_layout)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(HLINE_STYLE)
        self.frame_layout.addWidget(line)
        self.days_layout = QHBoxLayout()
        self.days_layout.setContentsMargins(5, 2, 5, 2)
        self.days_layout.setSpacing(15)
        self.frame_layout.addLayout(self.days_layout)
        self._root_layout.addWidget(self.frame)

    def set_expiries(self, expiries: list[date]) -> None:
        self.expiries = list(expiries)
        self._render()

    def select_expiry(self, d: date) -> None:
        for ed, btn in self.expiry_buttons.items():
            btn.setStyleSheet(DAY_BTN_SELECTED_STYLE if ed == d else DAY_BTN_STYLE)

    def _render(self) -> None:
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
            connect_btn(lambda _=False, dd=d: self._on_day_clicked(dd))
            self.days_layout.addWidget(btn)
            self.expiry_buttons[d] = btn
        self.days_layout.addStretch()
        if self.expiries:
            first = self.expiries[0]
            self.select_expiry(first)
            self.expiry_selected.emit(first)

    def _on_day_clicked(self, d: date) -> None:
        self.select_expiry(d)
        self.expiry_selected.emit(d)

    @staticmethod
    def _clear_layout(layout: QHBoxLayout | QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.deleteLater()
            child = item.layout()
            if child is not None:
                TimelineWidget._clear_layout(child)  # type: ignore[arg-type]
