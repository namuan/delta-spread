from collections.abc import Callable
from typing import TYPE_CHECKING, TypedDict, cast, override

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPainterPath, QPaintEvent
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..domain.models import OptionType
from .styles import (
    COLOR_DANGER_RED,
    COLOR_GRAY_300,
    COLOR_GRAY_700,
    COLOR_SUCCESS_GREEN,
    COLOR_TEXT_PRIMARY,
)

if TYPE_CHECKING:
    from collections.abc import Callable as TCallable


class OptionBadge(QWidget):
    def __init__(
        self,
        text: str,
        color_bg: str,
        *,
        is_call: bool = False,
        pointer_up: bool = False,
    ) -> None:
        super().__init__()
        self.text = text
        self.color_bg = color_bg
        self.is_call = is_call or ("CALL" in text.upper())
        self.pointer_up = pointer_up
        self._leg_idx: int | None = None
        self._toggle_handler: Callable[[int, OptionType], None] | None = None
        self.setFixedSize(50, 25)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_toggle_context(
        self,
        leg_idx: int,
        handler: Callable[[int, OptionType], None] | None,
    ) -> None:
        self._leg_idx = leg_idx
        self._toggle_handler = handler

    @override
    def paintEvent(self, a0: QPaintEvent | None) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        if self.pointer_up:
            path.addRoundedRect(0, 5, self.width(), self.height() - 5, 3, 3)
            path.moveTo(self.width() / 2 - 5, 5)
            path.lineTo(self.width() / 2, 0)
            path.lineTo(self.width() / 2 + 5, 5)
        else:
            path.addRoundedRect(0, 0, self.width(), self.height() - 5, 3, 3)
            path.moveTo(self.width() / 2 - 5, self.height() - 5)
            path.lineTo(self.width() / 2, self.height())
            path.lineTo(self.width() / 2 + 5, self.height() - 5)
        painter.fillPath(path, QColor(self.color_bg))
        painter.setPen(
            QColor(COLOR_TEXT_PRIMARY) if self.pointer_up else Qt.GlobalColor.white
        )
        painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        tgt_rect = (
            self.rect().adjusted(0, 5, 0, 0)
            if self.pointer_up
            else self.rect().adjusted(0, 0, 0, -5)
        )
        painter.drawText(tgt_rect, Qt.AlignmentFlag.AlignCenter, self.text)

    @override
    def mousePressEvent(self, a0: QMouseEvent | None) -> None:
        if a0 and a0.button() == Qt.MouseButton.LeftButton:
            popup = OptionDetailPopup(
                self,
                is_call=self.is_call,
                on_toggle=self._toggle_handler,
                leg_idx=self._leg_idx,
            )
            popup.adjustSize()
            anchor_local = QPoint(
                self.width() // 2, 0 if self.pointer_up else self.height()
            )
            anchor_global = self.mapToGlobal(anchor_local)
            x = anchor_global.x() - popup.width() // 2
            y = (
                anchor_global.y() - popup.height() - 8
                if self.pointer_up
                else anchor_global.y() + 8
            )
            popup.move(x, y)
            popup.show()
        super().mousePressEvent(a0)


class OptionDetailPopup(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        is_call: bool = True,
        on_toggle: Callable[[int, OptionType], None] | None = None,
        leg_idx: int | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet(
            f"background: white; border: 1px solid {COLOR_GRAY_300}; border-radius: 6px;"
        )
        self._is_call = is_call
        self._on_toggle = on_toggle
        self._leg_idx = leg_idx

        class PopupData(TypedDict):
            symbol: str
            strike: str
            expiration: str
            price: float
            bid: float
            ask: float
            volume: int
            oi: int
            iv: str
            delta: float
            theta: float
            gamma: float
            vega: float
            rho: float

        self._data: PopupData = {
            "symbol": "SPXW",
            "strike": "6540C" if self._is_call else "6540P",
            "expiration": "12/5/25",
            "price": 150.05,
            "bid": 149.30,
            "ask": 150.80,
            "volume": 39,
            "oi": 24,
            "iv": "21.2%",
            "delta": 0.616,
            "theta": -4.26,
            "gamma": 0.0014,
            "vega": 4.93,
            "rho": 1.50,
        }
        self._root = QVBoxLayout(self)
        self._root.setContentsMargins(10, 10, 10, 10)
        self._root.setSpacing(8)
        self._build_header()
        self._build_metrics()
        self._build_actions()
        self._connect_actions()

    def _build_header(self) -> None:
        header = QHBoxLayout()
        self._title_lbl = QLabel(
            f"{self._data["symbol"]} {self._data["strike"]} {self._data["expiration"]}"
        )
        header_color = COLOR_SUCCESS_GREEN if self._is_call else COLOR_DANGER_RED
        self._title_lbl.setStyleSheet(f"font-weight: bold; color: {header_color};")
        self._price_lbl = QLabel(f"Price\n{self._data["price"]:.2f}")
        self._price_lbl.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._price_lbl.setStyleSheet("font-weight: bold;")

        qty_row = QHBoxLayout()
        qty_label = QLabel("Quantity")
        qty_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        qty_spin = QSpinBox()
        qty_spin.setMinimum(1)
        qty_spin.setMaximum(99)
        qty_spin.setValue(1)
        qty_spin.setFixedWidth(60)
        qty_row.addWidget(qty_label)
        qty_row.addStretch(1)
        qty_row.addWidget(qty_spin)

        header.addWidget(self._title_lbl, 1)
        header.addWidget(self._price_lbl)
        self._root.addLayout(header)
        self._root.addLayout(qty_row)

    def _build_metrics(self) -> None:
        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(4)

        def metric(
            lbl: str, val: str, color: str | None = None
        ) -> tuple[QLabel, QLabel]:
            label_w = QLabel(lbl)
            label_w.setStyleSheet("font-size: 11px; color: #666;")
            value_w = QLabel(val)
            style = "font-weight: bold; font-size: 11px;"
            if color:
                style += f" color: {color};"
            value_w.setStyleSheet(style)
            return label_w, value_w

        lbl, val = metric("Bid", f"{self._data["bid"]:.2f}", COLOR_SUCCESS_GREEN)
        grid.addWidget(lbl, 0, 0)
        grid.addWidget(val, 0, 1)

        lbl, val = metric("Ask", f"{self._data["ask"]:.2f}", COLOR_DANGER_RED)
        grid.addWidget(lbl, 0, 2)
        grid.addWidget(val, 0, 3)

        lbl, val = metric("Volume", str(self._data["volume"]))
        grid.addWidget(lbl, 1, 0)
        grid.addWidget(val, 1, 1)

        lbl, val = metric("OI", str(self._data["oi"]))
        grid.addWidget(lbl, 1, 2)
        grid.addWidget(val, 1, 3)

        lbl, val = metric("IV", str(self._data["iv"]))
        grid.addWidget(lbl, 2, 0)
        grid.addWidget(val, 2, 1)

        lbl, val = metric("Delta", f"{self._data["delta"]:.3f}")
        grid.addWidget(lbl, 2, 2)
        grid.addWidget(val, 2, 3)

        lbl, val = metric("Theta", f"{self._data["theta"]:.2f}")
        grid.addWidget(lbl, 3, 0)
        grid.addWidget(val, 3, 1)

        lbl, val = metric("Gamma", f"{self._data["gamma"]:.4f}")
        grid.addWidget(lbl, 3, 2)
        grid.addWidget(val, 3, 3)

        lbl, val = metric("Vega", f"{self._data["vega"]:.2f}")
        grid.addWidget(lbl, 4, 0)
        grid.addWidget(val, 4, 1)

        lbl, val = metric("Rho", f"{self._data["rho"]:.2f}")
        grid.addWidget(lbl, 4, 2)
        grid.addWidget(val, 4, 3)

        self._root.addLayout(grid)

    def _build_actions(self) -> None:
        hline = QFrame()
        hline.setFrameShape(QFrame.Shape.HLine)
        hline.setStyleSheet(f"color: {COLOR_GRAY_700};")
        self._root.addWidget(hline)

        def action_button(text: str) -> QPushButton:
            b = QPushButton(text)
            b.setFlat(True)
            b.setStyleSheet(
                "text-align: left; border: none; padding: 4px 0; font-size: 12px;"
            )
            return b

        self._btn_switch = action_button(
            "Switch to Put" if self._is_call else "Switch to Call"
        )
        self._btn_sell_close = action_button("Sell to Close")
        self._btn_change_exp = action_button("Change Expiration")
        self._btn_exclude = action_button("Exclude")
        self._btn_remove = action_button("Remove")
        self._root.addWidget(self._btn_switch)
        self._root.addWidget(self._btn_sell_close)
        self._root.addWidget(self._btn_change_exp)
        self._root.addWidget(self._btn_exclude)
        self._root.addWidget(self._btn_remove)

    def _connect_actions(self) -> None:
        connect_switch: TCallable[..., object] = cast(
            "TCallable[..., object]", self._btn_switch.clicked.connect
        )
        connect_switch(self._on_switch_type)

    def _on_switch_type(self) -> None:
        self._is_call = not self._is_call
        base = self._data["strike"].rstrip("CP")
        self._data["strike"] = base + ("C" if self._is_call else "P")
        self._title_lbl.setText(
            f"{self._data["symbol"]} {self._data["strike"]} {self._data["expiration"]}"
        )
        header_color = COLOR_SUCCESS_GREEN if self._is_call else COLOR_DANGER_RED
        self._title_lbl.setStyleSheet(f"font-weight: bold; color: {header_color};")
        self._btn_switch.setText("Switch to Put" if self._is_call else "Switch to Call")
        if self._on_toggle is not None and self._leg_idx is not None:
            self._on_toggle(
                self._leg_idx,
                OptionType.CALL if self._is_call else OptionType.PUT,
            )
            self.close()
