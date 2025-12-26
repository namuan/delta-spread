"""Strategy state management service.

This module provides centralized strategy state management,
including CRUD operations for option legs and strategy validation.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from ..domain.models import (
    OptionContract,
    OptionLeg,
    Strategy,
)

if TYPE_CHECKING:
    from datetime import date

    from ..domain.models import OptionType, Underlier


class StrategyManager:
    """Manages strategy state and option leg operations.

    This class encapsulates all strategy mutation logic, providing
    a clean interface for adding, removing, and modifying option legs.
    """

    def __init__(self, strategy: Strategy | None = None) -> None:
        """Initialize the strategy manager.

        Args:
            strategy: Optional initial strategy to manage.
        """
        super().__init__()
        self._strategy = strategy
        self._logger = logging.getLogger(__name__)

    @property
    def strategy(self) -> Strategy | None:
        """Get the current strategy."""
        return self._strategy

    @strategy.setter
    def strategy(self, value: Strategy | None) -> None:
        """Set the current strategy."""
        self._strategy = value

    def has_strategy(self) -> bool:
        """Check if a strategy is currently set."""
        return self._strategy is not None

    def get_underlier(self) -> Underlier | None:
        """Get the underlier from the current strategy."""
        return self._strategy.underlier if self._strategy else None

    def get_legs(self) -> list[OptionLeg]:
        """Get the list of legs from the current strategy."""
        return list(self._strategy.legs) if self._strategy else []

    def create_strategy(
        self,
        name: str,
        underlier: Underlier,
        leg: OptionLeg,
    ) -> Strategy:
        """Create a new strategy with an initial leg.

        Args:
            name: Strategy name.
            underlier: The underlying asset.
            leg: Initial option leg.

        Returns:
            The newly created strategy.
        """
        self._strategy = Strategy(name=name, underlier=underlier, legs=[leg])
        self._logger.info(
            "Created strategy: %s %s @ %.2f",
            leg.side.name,
            leg.contract.type.name,
            leg.contract.strike,
        )
        return self._strategy

    def add_leg(self, leg: OptionLeg) -> Strategy:
        """Add a leg to the current strategy.

        Args:
            leg: The option leg to add.

        Returns:
            The updated strategy.

        Raises:
            ValueError: If no strategy exists.
        """
        if self._strategy is None:
            raise ValueError("Cannot add leg: no strategy exists")

        self._strategy = Strategy(
            name=self._strategy.name,
            underlier=self._strategy.underlier,
            legs=[*self._strategy.legs, leg],
            constraints=self._strategy.constraints,
        )
        self._logger.info(
            "Added leg: %s %s @ %.2f",
            leg.side.name,
            leg.contract.type.name,
            leg.contract.strike,
        )
        return self._strategy

    def remove_leg(self, leg_idx: int) -> Strategy | None:
        """Remove a leg from the strategy by index.

        Args:
            leg_idx: Index of the leg to remove.

        Returns:
            The updated strategy, or None if no legs remain.

        Raises:
            ValueError: If no strategy exists or index is invalid.
        """
        if self._strategy is None:
            raise ValueError("Cannot remove leg: no strategy exists")

        if leg_idx < 0 or leg_idx >= len(self._strategy.legs):
            raise ValueError(f"Invalid leg index: {leg_idx}")

        legs = [leg for i, leg in enumerate(self._strategy.legs) if i != leg_idx]

        if not legs:
            self._strategy = None
            self._logger.info("Removed last leg, strategy cleared")
            return None

        self._strategy = Strategy(
            name=self._strategy.name,
            underlier=self._strategy.underlier,
            legs=legs,
            constraints=self._strategy.constraints,
        )
        self._logger.info("Removed leg at index %d", leg_idx)
        return self._strategy

    def update_leg_type(
        self,
        leg_idx: int,
        new_type: OptionType,
        new_entry_price: float,
    ) -> Strategy:
        """Update the option type of a leg.

        Args:
            leg_idx: Index of the leg to update.
            new_type: New option type (CALL/PUT).
            new_entry_price: New entry price after type change.

        Returns:
            The updated strategy.

        Raises:
            ValueError: If no strategy exists or index is invalid.
        """
        if self._strategy is None:
            raise ValueError("Cannot update leg: no strategy exists")

        if leg_idx < 0 or leg_idx >= len(self._strategy.legs):
            raise ValueError(f"Invalid leg index: {leg_idx}")

        legs = list(self._strategy.legs)
        leg = legs[leg_idx]

        contract = OptionContract(
            underlier=leg.contract.underlier,
            expiry=leg.contract.expiry,
            strike=leg.contract.strike,
            type=new_type,
        )

        legs[leg_idx] = OptionLeg(
            contract=contract,
            side=leg.side,
            quantity=leg.quantity,
            entry_price=new_entry_price,
            notes=leg.notes,
        )

        self._strategy = Strategy(
            name=self._strategy.name,
            underlier=self._strategy.underlier,
            legs=legs,
            constraints=self._strategy.constraints,
        )
        self._logger.info(
            "Updated leg %d type to %s",
            leg_idx,
            new_type.name,
        )
        return self._strategy

    def update_leg_strike(
        self,
        leg_idx: int,
        new_strike: float,
        new_entry_price: float,
    ) -> Strategy:
        """Update the strike price of a leg.

        Args:
            leg_idx: Index of the leg to update.
            new_strike: New strike price.
            new_entry_price: New entry price after strike change.

        Returns:
            The updated strategy.

        Raises:
            ValueError: If no strategy exists or index is invalid.
        """
        if self._strategy is None:
            raise ValueError("Cannot update leg: no strategy exists")

        if leg_idx < 0 or leg_idx >= len(self._strategy.legs):
            raise ValueError(f"Invalid leg index: {leg_idx}")

        legs = list(self._strategy.legs)
        leg = legs[leg_idx]

        contract = OptionContract(
            underlier=leg.contract.underlier,
            expiry=leg.contract.expiry,
            strike=float(new_strike),
            type=leg.contract.type,
        )

        legs[leg_idx] = OptionLeg(
            contract=contract,
            side=leg.side,
            quantity=leg.quantity,
            entry_price=new_entry_price,
            notes=leg.notes,
        )

        self._strategy = Strategy(
            name=self._strategy.name,
            underlier=self._strategy.underlier,
            legs=legs,
            constraints=self._strategy.constraints,
        )
        self._logger.info(
            "Updated leg %d strike to %.2f",
            leg_idx,
            new_strike,
        )
        return self._strategy

    def create_preview_strategy(
        self,
        leg_idx: int,
        new_strike: float,
        new_entry_price: float,
    ) -> Strategy | None:
        """Create a preview strategy with a modified leg strike.

        This does not modify the current strategy state.

        Args:
            leg_idx: Index of the leg to modify in preview.
            new_strike: New strike price for preview.
            new_entry_price: New entry price for preview.

        Returns:
            A preview strategy, or None if no strategy exists.
        """
        if self._strategy is None:
            return None

        if leg_idx < 0 or leg_idx >= len(self._strategy.legs):
            return None

        legs = list(self._strategy.legs)
        leg = legs[leg_idx]

        contract = OptionContract(
            underlier=leg.contract.underlier,
            expiry=leg.contract.expiry,
            strike=float(new_strike),
            type=leg.contract.type,
        )

        legs[leg_idx] = OptionLeg(
            contract=contract,
            side=leg.side,
            quantity=leg.quantity,
            entry_price=new_entry_price,
            notes=leg.notes,
        )

        return Strategy(
            name=self._strategy.name,
            underlier=self._strategy.underlier,
            legs=legs,
            constraints=self._strategy.constraints,
        )

    def reset(self) -> None:
        """Reset the strategy to None."""
        self._strategy = None
        self._logger.info("Strategy reset")

    def update_leg_expiry(
        self,
        leg_idx: int,
        new_expiry: date,
        new_entry_price: float,
    ) -> Strategy:
        """Update the expiry of a single leg.

        Args:
            leg_idx: Index of the leg to update.
            new_expiry: New expiry date.
            new_entry_price: New entry price for the leg at new expiry.

        Returns:
            The updated strategy.

        Raises:
            ValueError: If no strategy exists or index is invalid.
        """
        if self._strategy is None:
            raise ValueError("Cannot update leg: no strategy exists")

        if leg_idx < 0 or leg_idx >= len(self._strategy.legs):
            raise ValueError(f"Invalid leg index: {leg_idx}")

        legs = list(self._strategy.legs)
        leg = legs[leg_idx]

        contract = OptionContract(
            underlier=leg.contract.underlier,
            expiry=new_expiry,
            strike=leg.contract.strike,
            type=leg.contract.type,
        )

        legs[leg_idx] = OptionLeg(
            contract=contract,
            side=leg.side,
            quantity=leg.quantity,
            entry_price=new_entry_price,
            notes=leg.notes,
        )

        self._strategy = Strategy(
            name=self._strategy.name,
            underlier=self._strategy.underlier,
            legs=legs,
            constraints=self._strategy.constraints,
        )
        self._logger.info(
            "Updated leg %d expiry to %s with price %.2f",
            leg_idx,
            new_expiry,
            new_entry_price,
        )
        return self._strategy

    def get_expiry_for_new_leg(self, selected_expiry: date | None) -> date | None:
        """Get the appropriate expiry for a new leg.

        If the strategy has same_expiry constraint and existing legs,
        returns the expiry from the first leg. Otherwise returns
        the selected expiry.

        Args:
            selected_expiry: The currently selected expiry date.

        Returns:
            The expiry date to use for a new leg.
        """
        if (
            self._strategy is not None
            and self._strategy.constraints.same_expiry
            and self._strategy.legs
        ):
            return self._strategy.legs[0].contract.expiry
        return selected_expiry
