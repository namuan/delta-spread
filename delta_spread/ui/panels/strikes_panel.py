"""Strikes panel component.

This module provides a panel for displaying the strike ruler
with label and handling strike-related operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ..strike_ruler import StrikeRuler
from ..styles import MONTH_LABEL_STYLE

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..strike_ruler import BadgeSpec


class StrikesPanel(QWidget):
    """Panel for displaying the strike ruler.

    This widget wraps the StrikeRuler with a label and
    provides a clean interface for strike operations.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the strikes panel.

        Args:
            parent: Parent widget.
        """
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the panel UI."""
        self.setFixedHeight(120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel("STRIKES:")
        lbl.setStyleSheet(MONTH_LABEL_STYLE)
        layout.addWidget(lbl)

        self.strike_ruler = StrikeRuler()
        self.strike_ruler.setFixedHeight(100)
        layout.addWidget(self.strike_ruler)

    def set_toggle_handler(self, handler: Callable[[int, object], None]) -> None:
        """Set the badge toggle handler.

        Args:
            handler: Callback for badge toggle events.
        """
        self.strike_ruler.set_toggle_handler(handler)

    def set_remove_handler(self, handler: Callable[[int], None]) -> None:
        """Set the badge remove handler.

        Args:
            handler: Callback for badge remove events.
        """
        self.strike_ruler.set_remove_handler(handler)

    def set_move_handler(self, handler: Callable[[int, float], None]) -> None:
        """Set the badge move handler.

        Args:
            handler: Callback for badge move events.
        """
        self.strike_ruler.set_move_handler(handler)

    def set_preview_handler(self, handler: Callable[[int, float], None]) -> None:
        """Set the badge preview move handler.

        Args:
            handler: Callback for badge preview move events.
        """
        self.strike_ruler.set_preview_handler(handler)

    def set_strikes(self, strikes: list[float]) -> None:
        """Set the available strikes.

        Args:
            strikes: List of strike prices.
        """
        self.strike_ruler.set_strikes(strikes)

    def set_selected_strikes(self, strikes: list[float]) -> None:
        """Set the selected strikes.

        Args:
            strikes: List of selected strike prices.
        """
        self.strike_ruler.set_selected_strikes(strikes)

    def set_badges(self, badges: list[BadgeSpec]) -> None:
        """Set the badge specifications.

        Args:
            badges: List of badge specifications.
        """
        self.strike_ruler.set_badges(badges)

    def set_current_price(self, price: float, symbol: str) -> None:
        """Set the current price marker.

        Args:
            price: Current price.
            symbol: Symbol for the price marker.
        """
        self.strike_ruler.set_current_price(price, symbol)

    def center_on_value(self, value: float) -> None:
        """Center the ruler on a specific value.

        Args:
            value: Value to center on.
        """
        self.strike_ruler.center_on_value(value)

    def get_center_strike(self) -> float | None:
        """Get the center strike value.

        Returns:
            The center strike value or None.
        """
        return self.strike_ruler.get_center_strike()

    def get_current_price(self) -> float | None:
        """Get the current price.

        Returns:
            The current price or None.
        """
        return self.strike_ruler.get_current_price()
