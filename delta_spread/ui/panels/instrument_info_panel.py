"""Instrument info panel component.

This module provides a panel for displaying instrument information
including symbol input, price, change, and action buttons.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from PyQt6.QtCore import QPoint, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QWidget,
)

from ..styles import (
    BUTTON_PRIMARY_STYLE,
    CHANGE_LABEL_STYLE,
    LOADING_INDICATOR_STYLE,
    PRICE_LABEL_STYLE,
    REALTIME_LABEL_STYLE,
    RT_HELP_STYLE,
    SYMBOL_INPUT_STYLE,
)

if TYPE_CHECKING:
    from collections.abc import Callable as TCallable

    from PyQt6.QtWidgets import QMenu

    from ...data.tradier_data import StockQuote


class InstrumentInfoPanel(QWidget):
    """Panel for displaying instrument information.

    This widget contains the symbol input, price display,
    change display, and action buttons.
    """

    # Signals
    symbol_changed = pyqtSignal(str)
    add_clicked = pyqtSignal()
    positions_clicked = pyqtSignal()
    save_clicked = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the instrument info panel.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._add_menu: QMenu | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the panel UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)

        # Symbol input
        self.symbol_input = QLineEdit("SPY")
        self.symbol_input.setFixedWidth(60)
        self.symbol_input.setStyleSheet(SYMBOL_INPUT_STYLE)

        connect_return: TCallable[..., object] = cast(
            "TCallable[..., object]", self.symbol_input.returnPressed.connect
        )
        connect_return(self._on_symbol_changed)

        connect_edit: TCallable[..., object] = cast(
            "TCallable[..., object]", self.symbol_input.editingFinished.connect
        )
        connect_edit(self._on_symbol_changed)

        # Price and change labels
        self.price_label = QLabel("--")
        self.price_label.setStyleSheet(PRICE_LABEL_STYLE)

        self.change_label = QLabel("--\n--")
        self.change_label.setStyleSheet(CHANGE_LABEL_STYLE)

        # Real-time indicator
        realtime_label = QLabel("Real-time")
        realtime_label.setStyleSheet(REALTIME_LABEL_STYLE)

        rt_help = QLabel("?")
        rt_help.setStyleSheet(RT_HELP_STYLE)

        # Add widgets
        layout.addWidget(self.symbol_input)
        layout.addSpacing(10)
        layout.addWidget(self.price_label)
        layout.addSpacing(10)
        layout.addWidget(self.change_label)
        layout.addSpacing(15)
        layout.addWidget(realtime_label)
        layout.addWidget(rt_help)
        layout.addStretch()

        # Loading indicator (before action buttons to avoid layout shift)
        self._loading_indicator = QProgressBar()
        self._loading_indicator.setFixedWidth(60)
        self._loading_indicator.setFixedHeight(14)
        self._loading_indicator.setRange(0, 0)  # Indeterminate mode
        self._loading_indicator.setTextVisible(False)
        self._loading_indicator.setStyleSheet(LOADING_INDICATOR_STYLE)
        self._loading_indicator.hide()  # Hidden by default
        layout.addWidget(self._loading_indicator)
        layout.addSpacing(8)

        # Action buttons
        self.btn_add = QPushButton("Add +")
        self.btn_pos = QPushButton("Positions")
        self.btn_save = QPushButton("Save Trade")

        for btn in [self.btn_add, self.btn_pos, self.btn_save]:
            btn.setStyleSheet(BUTTON_PRIMARY_STYLE)
            layout.addWidget(btn)

        # Connect button signals
        connect_add: TCallable[..., object] = cast(
            "TCallable[..., object]", self.btn_add.clicked.connect
        )
        connect_add(self._on_add_clicked)

        connect_pos: TCallable[..., object] = cast(
            "TCallable[..., object]", self.btn_pos.clicked.connect
        )
        connect_pos(self.positions_clicked.emit)

        connect_save: TCallable[..., object] = cast(
            "TCallable[..., object]", self.btn_save.clicked.connect
        )
        connect_save(self.save_clicked.emit)

    def _on_symbol_changed(self) -> None:
        """Handle symbol input change."""
        symbol = self.symbol_input.text().strip()
        if symbol:
            self.symbol_changed.emit(symbol)

    def _on_add_clicked(self) -> None:
        """Handle add button click."""
        if self._add_menu is not None:
            self.show_add_menu()
        else:
            self.add_clicked.emit()

    def set_add_menu(self, menu: QMenu) -> None:
        """Set the add menu.

        Args:
            menu: The menu to show when add is clicked.
        """
        self._add_menu = menu

    def show_add_menu(self) -> None:
        """Show the add menu below the add button."""
        if self._add_menu is None:
            return

        p = self.btn_add.mapToGlobal(self.btn_add.rect().bottomLeft())
        p = QPoint(p.x() + 8, p.y() + 4)
        self._add_menu.popup(p)

    def get_symbol(self) -> str:
        """Get the current symbol.

        Returns:
            The current symbol text.
        """
        return self.symbol_input.text().strip()

    def set_symbol(self, symbol: str) -> None:
        """Set the symbol input text.

        Args:
            symbol: The symbol to set.
        """
        self.symbol_input.setText(symbol)

    def update_price(self, price_text: str) -> None:
        """Update the price label.

        Args:
            price_text: Formatted price text.
        """
        self.price_label.setText(price_text)

    def update_change(self, change_text: str) -> None:
        """Update the change label.

        Args:
            change_text: Formatted change text with percentage.
        """
        self.change_label.setText(change_text)

    def update_quote(self, quote: StockQuote | None) -> None:
        """Update the display with quote data.

        Args:
            quote: Quote dict with 'last', 'change', 'change_percentage' keys,
                   or None to clear the display.
        """
        if quote is None:
            self.price_label.setText("--")
            self.change_label.setText("--\n--")
            return

        # Format price with commas
        price = quote["last"]
        price_str = f"{price:,.2f}"
        self.price_label.setText(price_str)

        # Format change and percentage
        change = quote["change"]
        change_pct = quote["change_percentage"]
        sign = "+" if change >= 0 else ""
        change_str = f"{sign}{change_pct:.2f}%\n{sign}{change:.2f}"
        self.change_label.setText(change_str)

    def show_loading(self) -> None:
        """Show the loading indicator."""
        self._loading_indicator.show()

    def hide_loading(self) -> None:
        """Hide the loading indicator."""
        self._loading_indicator.hide()

    def set_loading(self, *, is_loading: bool) -> None:
        """Set the loading indicator visibility.

        Args:
            is_loading: Whether to show the loading indicator.
        """
        if is_loading:
            self._loading_indicator.show()
        else:
            self._loading_indicator.hide()
