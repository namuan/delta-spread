from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, TypedDict, cast, override

from PyQt6.QtCore import QPoint, QRect, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPainterPath, QPaintEvent
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
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
    COLOR_HOVER_BLUE,
    COLOR_SUCCESS_GREEN,
    COLOR_TEXT_PRIMARY,
)

if TYPE_CHECKING:
    from collections.abc import Callable as TCallable


class OptionDetailData(TypedDict):
    """Data structure for option detail popup."""

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


class _HasStrikeAtX(Protocol):
    def strike_at_x(self, x_local: int) -> float: ...


class _HasDragHighlight(Protocol):
    def set_drag_highlight(self, strike: float | None) -> None: ...


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
        self._remove_handler: Callable[[int], None] | None = None
        self._move_handler: Callable[[int, float], None] | None = None
        self._preview_handler: Callable[[int, float], None] | None = None
        self._detail_data_provider: Callable[[int], OptionDetailData | None] | None = (
            None
        )
        self._press_x: int = 0
        self._press_y: int = 0
        self._drag_start_x: int = 0
        self._drag_start_y: int = 0
        self._dragging: bool = False
        self._drag_threshold: int = 7
        self._multi_count: int = 1
        self._badge_siblings: list[OptionBadge] = []
        self._preview_debounce_timer: QTimer = QTimer(self)
        self._preview_debounce_timer.setSingleShot(True)
        self._preview_debounce_timer.setInterval(150)  # 150ms debounce
        self._preview_debounce_timer.timeout.connect(  # pyright: ignore[reportUnknownMemberType]
            self._emit_debounced_preview
        )
        self._pending_preview_strike: float | None = None
        self.setFixedSize(50, 25)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_toggle_context(
        self,
        leg_idx: int,
        handler: Callable[[int, OptionType], None] | None,
    ) -> None:
        self._leg_idx = leg_idx
        self._toggle_handler = handler

    def set_remove_context(
        self,
        leg_idx: int,
        handler: Callable[[int], None] | None,
    ) -> None:
        self._leg_idx = leg_idx
        self._remove_handler = handler

    def set_move_context(
        self,
        leg_idx: int,
        handler: Callable[[int, float], None] | None,
    ) -> None:
        self._leg_idx = leg_idx
        self._move_handler = handler

    def set_preview_context(
        self,
        leg_idx: int,
        handler: Callable[[int, float], None] | None,
    ) -> None:
        self._leg_idx = leg_idx
        self._preview_handler = handler

    def set_detail_data_provider(
        self,
        provider: Callable[[int], "OptionDetailData | None"] | None,
    ) -> None:
        """Set the provider for fetching real-time option detail data."""
        self._detail_data_provider = provider

    def get_detail_data(self) -> "OptionDetailData | None":
        """Get real-time option detail data for this badge."""
        if self._detail_data_provider is not None and self._leg_idx is not None:
            return self._detail_data_provider(self._leg_idx)
        return None

    def set_badge_siblings(self, siblings: list["OptionBadge"]) -> None:
        """Set the list of all badges at the same strike/placement position."""
        self._badge_siblings = siblings

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

        if self._multi_count > 1:
            bubble_d = 14
            bx = self.width() - bubble_d - 2
            by = 2 if self.pointer_up else self.height() - bubble_d - 7
            painter.setBrush(QColor(COLOR_TEXT_PRIMARY))
            painter.setPen(Qt.GlobalColor.white)
            painter.drawEllipse(bx, by, bubble_d, bubble_d)
            painter.setFont(QFont("Arial", 8, QFont.Weight.Bold))
            painter.drawText(
                QRect(bx, by, bubble_d, bubble_d),
                Qt.AlignmentFlag.AlignCenter,
                str(self._multi_count),
            )

    @override
    def mousePressEvent(self, a0: QMouseEvent | None) -> None:
        if a0 and a0.button() == Qt.MouseButton.LeftButton:
            self._press_x = int(a0.position().x())
            self._press_y = int(a0.position().y())
            self._drag_start_x = self.x()
            self._drag_start_y = self.y()
            self._dragging = False
            a0.accept()
            return
        super().mousePressEvent(a0)

    @override
    def mouseMoveEvent(self, a0: QMouseEvent | None) -> None:
        if a0 is None or not (a0.buttons() & Qt.MouseButton.LeftButton):
            super().mouseMoveEvent(a0)
            return
        parent = self.parentWidget()
        if parent is None:
            a0.accept()
            return
        gp = a0.globalPosition()
        parent_pos = parent.mapFromGlobal(gp.toPoint())
        dx = int(parent_pos.x()) - (self._drag_start_x + self._press_x)
        if not self._dragging and abs(dx) >= self._drag_threshold:
            self._dragging = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.raise_()
        if not self._dragging:
            a0.accept()
            return
        new_x = self._drag_start_x + dx
        max_x = max(0, parent.width() - self.width())
        new_x = max(new_x, 0)
        new_x = min(new_x, max_x)
        self.move(new_x, self._drag_start_y)
        if hasattr(parent, "strike_at_x") and hasattr(parent, "set_drag_highlight"):
            centre_x = new_x + (self.width() // 2)
            strike = cast("_HasStrikeAtX", parent).strike_at_x(centre_x)
            cast("_HasDragHighlight", parent).set_drag_highlight(float(strike))
            if self._preview_handler is not None and self._leg_idx is not None:
                self._pending_preview_strike = float(strike)
                self._preview_debounce_timer.start()
        a0.accept()
        return

    def _emit_debounced_preview(self) -> None:
        """Emit the debounced preview after the timer fires."""
        if (
            self._preview_handler is not None
            and self._leg_idx is not None
            and self._pending_preview_strike is not None
        ):
            self._preview_handler(self._leg_idx, self._pending_preview_strike)

    @override
    def mouseReleaseEvent(self, a0: QMouseEvent | None) -> None:
        if not (a0 and a0.button() == Qt.MouseButton.LeftButton):
            super().mouseReleaseEvent(a0)
            return
        if self._dragging:
            # Stop debounce timer and clear pending preview on drag end
            self._preview_debounce_timer.stop()
            self._pending_preview_strike = None
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            parent = self.parentWidget()
            if (
                parent is not None
                and self._move_handler is not None
                and self._leg_idx is not None
                and hasattr(parent, "strike_at_x")
            ):
                centre_x = self.x() + (self.width() // 2)
                new_strike = cast("_HasStrikeAtX", parent).strike_at_x(centre_x)
                self._move_handler(self._leg_idx, float(new_strike))
                if hasattr(parent, "set_drag_highlight"):
                    cast("_HasDragHighlight", parent).set_drag_highlight(None)
            self._dragging = False
            a0.accept()
            return

        # If multiple badges at same position, show selection menu
        if self._multi_count > 1 and len(self._badge_siblings) > 1:
            menu = BadgeSelectionMenu(self, self._badge_siblings)
            anchor_local = QPoint(
                self.width() // 2, 0 if self.pointer_up else self.height()
            )
            anchor_global = self.mapToGlobal(anchor_local)
            x = anchor_global.x() - menu.width() // 2
            y = (
                anchor_global.y() - menu.height() - 8
                if self.pointer_up
                else anchor_global.y() + 8
            )
            menu.move(x, y)
            menu.show()
            a0.accept()
            return

        # Single badge or no siblings - show popup directly
        detail_data = self.get_detail_data()
        popup = OptionDetailPopup(
            self,
            is_call=self.is_call,
            handlers=PopupHandlers(
                on_toggle=self._toggle_handler,
                on_remove=self._remove_handler,
            ),
            leg_idx=self._leg_idx,
            detail_data=detail_data,
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
        a0.accept()
        return

    def is_dragging(self) -> bool:
        return self._dragging

    def set_multi_count(self, count: int) -> None:
        self._multi_count = max(1, int(count))
        self.update()

    def leg_index(self) -> int | None:
        return self._leg_idx

    def toggle_handler(self) -> Callable[[int, OptionType], None] | None:
        return self._toggle_handler

    def remove_handler(self) -> Callable[[int], None] | None:
        return self._remove_handler


class BadgeSelectionMenu(QDialog):
    """Menu to select which badge's popup to display when multiple badges are at the same position."""

    def __init__(
        self,
        parent: QWidget | None = None,
        badges: list[OptionBadge] | None = None,
    ) -> None:
        super().__init__(parent)
        self._badges = badges or []
        self._setup_window()
        self._build_ui()

    def _setup_window(self) -> None:
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        style_dialog = "".join([
            "QDialog {",
            "  background: qlineargradient(x1:0, y1:0, x2:0, y2:1, ",
            f"    stop:0 white, stop:1 {COLOR_GRAY_300});",
            "  border: 2px solid #d0d0d0;",
            "  border-radius: 10px;",
            "}",
        ])
        self.setStyleSheet(style_dialog)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)
        for idx, badge in enumerate(self._badges):
            self._add_badge_item(layout, badge, idx)
        self.adjustSize()

    def _on_item_click(self, b: OptionBadge) -> Callable[[QMouseEvent | None], None]:
        def mouse_press(event: QMouseEvent | None) -> None:
            if event is not None and event.button() == Qt.MouseButton.LeftButton:
                self.close()
                detail_data = b.get_detail_data()
                popup = OptionDetailPopup(
                    b,
                    is_call=b.is_call,
                    handlers=PopupHandlers(
                        on_toggle=b.toggle_handler(),
                        on_remove=b.remove_handler(),
                    ),
                    leg_idx=b.leg_index(),
                    detail_data=detail_data,
                )
                popup.adjustSize()
                anchor_local = QPoint(b.width() // 2, 0 if b.pointer_up else b.height())
                anchor_global = b.mapToGlobal(anchor_local)
                x = anchor_global.x() - popup.width() // 2
                y = (
                    anchor_global.y() - popup.height() - 8
                    if b.pointer_up
                    else anchor_global.y() + 8
                )
                popup.move(x, y)
                popup.show()

        return mouse_press

    def _add_badge_item(
        self, layout: QVBoxLayout, badge: OptionBadge, idx: int
    ) -> None:
        clickable = self._build_clickable_container(badge)
        item_layout = QHBoxLayout(clickable)
        item_layout.setContentsMargins(12, 6, 8, 6)
        item_layout.setSpacing(8)
        # Indicator (color circle)
        indicator = QLabel("●")
        indicator_color = COLOR_SUCCESS_GREEN if badge.is_call else COLOR_DANGER_RED
        indicator.setStyleSheet(
            "".join([
                f"color: {indicator_color}; ",
                "font-size: 14px; ",
                "font-weight: bold;",
                "padding-top: 1px;",
            ])
        )
        indicator.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        indicator.setFixedWidth(20)
        item_layout.addWidget(indicator)

        # Prepare badge text with leg info
        leg_val = badge.leg_index()
        leg_text = f"Leg {leg_val}" if leg_val is not None else "Unknown"
        label_text = f"{badge.text} ({leg_text})"
        label = QLabel(label_text)
        label.setStyleSheet(
            "".join([
                "font-size: 11px; ",
                f"color: {COLOR_TEXT_PRIMARY};",
            ])
        )
        # Stretch before label to push it right
        item_layout.addStretch()
        item_layout.addWidget(
            label, alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
        )
        # Final stretch for tidy layout
        item_layout.addStretch()
        clickable.setCursor(Qt.CursorShape.PointingHandCursor)
        clickable.setStyleSheet(
            "".join([
                "QWidget {",
                "  background: transparent; ",
                "  border-radius: 6px; ",
                "  padding: 4px;",
                "}",
                "QWidget:hover {",
                f"  background-color: {COLOR_HOVER_BLUE}; ",
                "}",
            ])
        )
        layout.addWidget(clickable)
        if idx < len(self._badges) - 1:
            divider = QFrame()
            divider.setFrameShape(QFrame.Shape.HLine)
            divider.setStyleSheet(
                "".join([
                    f"background-color: {COLOR_GRAY_300}; ",
                    "border: none; ",
                    "height: 1px; ",
                    "margin: 0px 8px;",
                ])
            )
            layout.addWidget(divider)

    def _build_clickable_container(self, badge: OptionBadge) -> QWidget:
        item_container_click = self._on_item_click(badge)

        class _ClickableItem(QWidget):
            def __init__(self, parent: QWidget | None = None) -> None:
                super().__init__(parent)
                self._on_click: Callable[[QMouseEvent | None], None] = (
                    item_container_click
                )

            @override
            def mousePressEvent(self, a0: QMouseEvent | None) -> None:
                self._on_click(a0)

        return _ClickableItem()


@dataclass
class PopupHandlers:
    on_toggle: Callable[[int, OptionType], None] | None = None
    on_remove: Callable[[int], None] | None = None


class OptionDetailPopup(QDialog):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        is_call: bool = True,
        handlers: PopupHandlers | None = None,
        leg_idx: int | None = None,
        detail_data: OptionDetailData | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setStyleSheet(
            f"background: white; border: 1px solid {COLOR_GRAY_300}; border-radius: 6px;"
        )
        self._is_call = is_call
        self._handlers = handlers or PopupHandlers()
        self._on_toggle = self._handlers.on_toggle
        self._on_remove = self._handlers.on_remove
        self._leg_idx = leg_idx

        # Use provided real-time data or fallback to defaults
        if detail_data is not None:
            self._data: OptionDetailData = detail_data
        else:
            self._data = {
                "symbol": "SPXW",
                "strike": "6540C" if self._is_call else "6540P",
                "expiration": "12/5/25",
                "price": 0.0,
                "bid": 0.0,
                "ask": 0.0,
                "volume": 0,
                "oi": 0,
                "iv": "0.0%",
                "delta": 0.0,
                "theta": 0.0,
                "gamma": 0.0,
                "vega": 0.0,
                "rho": 0.0,
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
                "QPushButton { text-align: left; border: none; padding: 4px 0; font-size: 12px; }"
                + f"\nQPushButton:hover {{ background-color: {COLOR_HOVER_BLUE}; }}"
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
        connect_remove: TCallable[..., object] = cast(
            "TCallable[..., object]", self._btn_remove.clicked.connect
        )
        connect_remove(self._on_remove_clicked)

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

    def _on_remove_clicked(self) -> None:
        if self._on_remove is not None and self._leg_idx is not None:
            self._on_remove(self._leg_idx)
            self.close()
