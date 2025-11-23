from datetime import date
from typing import TYPE_CHECKING, cast

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QScroller,
    QVBoxLayout,
    QWidget,
)

from .styles import (
    DAY_BTN_SELECTED_STYLE,
    DAY_BTN_STYLE,
    HLINE_STYLE,
    MONTH_BAR_STYLE,
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

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        vp = self.scroll_area.viewport()
        if vp is not None:
            QScroller.grabGesture(
                vp, QScroller.ScrollerGestureType.LeftMouseButtonGesture
            )

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setSpacing(0)

        self.month_layout = QHBoxLayout()
        self.month_layout.setContentsMargins(10, 2, 10, 2)
        self.scroll_layout.addLayout(self.month_layout)

        self.line = QFrame()
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setStyleSheet(HLINE_STYLE)
        self.scroll_layout.addWidget(self.line)

        self.days_layout = QHBoxLayout()
        self.days_layout.setContentsMargins(5, 2, 5, 2)
        self.days_layout.setSpacing(15)
        self.scroll_layout.addLayout(self.days_layout)

        self.scroll_area.setWidget(self.scroll_content)
        self.frame_layout.addWidget(self.scroll_area)
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
        self.month_layout.setSpacing(self.days_layout.spacing())
        segments = self._compute_month_segments()
        day_w = 24
        for text, count in segments:
            seg = QLabel(text)
            seg.setStyleSheet(MONTH_BAR_STYLE)
            seg.setAlignment(Qt.AlignmentFlag.AlignCenter)
            spacing = max(self.days_layout.spacing(), 0)
            width = count * day_w + max(count - 1, 0) * spacing
            seg.setMinimumWidth(width)
            seg.setFixedHeight(22)
            self.month_layout.addWidget(seg)
        self.expiry_buttons = {}
        for d in self.expiries:
            btn = QPushButton(d.strftime("%d"))
            btn.setStyleSheet(DAY_BTN_STYLE)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedWidth(24)
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

    def _compute_month_segments(self) -> list[tuple[str, int]]:
        exps = self.expiries
        if not exps:
            return []
        base_year = exps[0].year
        segments: list[tuple[str, int]] = []
        current = exps[0]
        count = 0
        for d in exps:
            same = d.month == current.month and d.year == current.year
            if same:
                count += 1
                continue
            label = current.strftime("%b")
            if current.year != base_year:
                label = f"{label} '{current.strftime("%y")}"
            segments.append((label, count))
            current = d
            count = 1
        label = current.strftime("%b")
        if current.year != base_year:
            label = f"{label} '{current.strftime("%y")}"
        segments.append((label, count))
        return segments
