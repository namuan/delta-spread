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

    from ..option_badge import OptionDetailData
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

    def set_interaction_handlers(
        self,
        *,
        on_toggle: Callable[[int, object], None] | None = None,
        on_remove: Callable[[int], None] | None = None,
        on_move: Callable[[int, float], None] | None = None,
        on_preview: Callable[[int, float], None] | None = None,
    ) -> None:
        """Set interaction handlers for the strike ruler.

        Args:
            on_toggle: Callback for badge toggle events.
            on_remove: Callback for badge remove events.
            on_move: Callback for badge move events.
            on_preview: Callback for badge preview move events.
        """
        # wrapper to cast object to OptionType if needed, though handler signature in ruler is specific
        self.strike_ruler.set_interaction_handlers(
            on_toggle=on_toggle,
            on_remove=on_remove,
            on_move=on_move,
            on_preview=on_preview,
        )

    def set_detail_data_provider(
        self, provider: Callable[[int], OptionDetailData | None]
    ) -> None:
        """Set the provider for fetching real-time option detail data.

        Args:
            provider: Callback that takes leg_idx and returns option detail data.
        """
        self.strike_ruler.set_detail_data_provider(provider)

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
