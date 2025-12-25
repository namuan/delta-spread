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
        self.scroll_layout = QHBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(5, 0, 5, 0)
        self.scroll_layout.setSpacing(12)

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
        self._clear_layout(self.scroll_layout)
        self.expiry_buttons = {}

        month_groups = self._group_expiries_by_month()

        # Create a column for each month with header and day buttons below
        for month_label, days in month_groups:
            month_container = QWidget()
            month_vlayout = QVBoxLayout(month_container)
            month_vlayout.setContentsMargins(0, 0, 0, 0)
            month_vlayout.setSpacing(4)

            # Month header
            header = QLabel(month_label)
            header.setStyleSheet(MONTH_BAR_STYLE)
            header.setAlignment(Qt.AlignmentFlag.AlignCenter)
            header.setFixedHeight(18)
            month_vlayout.addWidget(header)

            # Days row for this month
            days_row = QHBoxLayout()
            days_row.setContentsMargins(0, 0, 0, 0)
            days_row.setSpacing(6)
            for d in days:
                btn = QPushButton(d.strftime("%d"))
                btn.setStyleSheet(DAY_BTN_STYLE)
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setFixedWidth(24)
                connect_btn: TCallable[..., object] = cast(
                    "TCallable[..., object]", btn.clicked.connect
                )
                connect_btn(lambda _=False, dd=d: self._on_day_clicked(dd))
                days_row.addWidget(btn)
                self.expiry_buttons[d] = btn
            month_vlayout.addLayout(days_row)
            self.scroll_layout.addWidget(month_container)

        self.scroll_layout.addStretch()
        if self.expiries:
            first = self.expiries[0]
            self.select_expiry(first)
            self.expiry_selected.emit(first)

    def _group_expiries_by_month(self) -> list[tuple[str, list[date]]]:
        month_groups: list[tuple[str, list[date]]] = []
        if not self.expiries:
            return month_groups

        base_year = self.expiries[0].year
        current_month: date | None = None
        current_list: list[date] = []

        for d in self.expiries:
            if (
                current_month is None
                or d.month != current_month.month
                or d.year != current_month.year
            ):
                if current_list and current_month:
                    label = self._create_month_label(current_month, base_year)
                    month_groups.append((label, current_list))
                current_month = d
                current_list = [d]
            else:
                current_list.append(d)

        if current_list and current_month:
            label = self._create_month_label(current_month, base_year)
            month_groups.append((label, current_list))

        return month_groups

    @staticmethod
    def _create_month_label(month_date: date, base_year: int) -> str:
        label = month_date.strftime("%b")
        if month_date.year != base_year:
            label = f"{label} '{month_date.strftime("%y")}"
        return label

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
