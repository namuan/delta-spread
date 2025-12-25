"""Quote service facade.

This module provides a centralized interface for fetching quotes
and implied volatility data from the options data service.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date

    from ..data.options_data import OptionsDataService
    from ..data.tradier_data import StockQuote
    from ..domain.models import OptionLeg, OptionQuote, OptionType, Strategy


class QuoteService:
    """Facade for quote-related operations.

    This class centralizes all quote fetching logic and provides
    caching for implied volatility values.
    """

    def __init__(self, data_service: OptionsDataService) -> None:
        """Initialize the quote service.

        Args:
            data_service: The underlying options data service.
        """
        super().__init__()
        self._data_service = data_service
        self._logger = logging.getLogger(__name__)

    @property
    def data_service(self) -> OptionsDataService:
        """Get the underlying data service."""
        return self._data_service

    @data_service.setter
    def data_service(self, value: OptionsDataService) -> None:
        """Set the underlying data service."""
        self._data_service = value

    def get_quote(
        self,
        symbol: str,
        expiry: date,
        strike: float,
        option_type: OptionType,
    ) -> OptionQuote:
        """Get a quote for a specific option.

        Args:
            symbol: Underlying symbol.
            expiry: Option expiry date.
            strike: Strike price.
            option_type: CALL or PUT.

        Returns:
            The option quote.
        """
        return self._data_service.get_quote(symbol, expiry, strike, option_type)

    def get_quote_for_leg(self, leg: OptionLeg, symbol: str) -> OptionQuote:
        """Get a quote for an option leg.

        Args:
            leg: The option leg.
            symbol: Underlying symbol.

        Returns:
            The option quote for this leg.
        """
        return self._data_service.get_quote(
            symbol,
            leg.contract.expiry,
            leg.contract.strike,
            leg.contract.type,
        )

    def get_ivs_for_strategy(
        self,
        strategy: Strategy,
    ) -> dict[tuple[float, OptionType], float]:
        """Get implied volatilities for all legs in a strategy.

        Args:
            strategy: The strategy to get IVs for.

        Returns:
            Dictionary mapping (strike, option_type) to IV.
        """
        ivs: dict[tuple[float, OptionType], float] = {}
        for leg in strategy.legs:
            quote = self._data_service.get_quote(
                strategy.underlier.symbol,
                leg.contract.expiry,
                leg.contract.strike,
                leg.contract.type,
            )
            ivs[leg.contract.strike, leg.contract.type] = quote.iv
        return ivs

    def get_expiries(self) -> list[date]:
        """Get available expiry dates.

        Returns:
            List of available expiry dates.
        """
        return list(self._data_service.get_expiries())

    def get_strikes(self, symbol: str, expiry: date) -> list[float]:
        """Get available strikes for a symbol and expiry.

        Args:
            symbol: Underlying symbol.
            expiry: Option expiry date.

        Returns:
            List of available strike prices.
        """
        return list(self._data_service.get_strikes(symbol, expiry))

    def get_stock_quote(self, symbol: str) -> StockQuote | None:  # noqa: ARG002
        """Get stock quote data.

        Args:
            symbol: Stock symbol (unused, kept for API consistency).

        Returns:
            Quote data dict with 'last', 'change', 'change_percentage' keys,
            or None if not available.
        """
        # Import here to avoid circular imports
        from ..data.tradier_data import TradierOptionsDataService  # noqa: PLC0415

        if isinstance(self._data_service, TradierOptionsDataService):
            try:
                return self._data_service.get_stock_quote()
            except (ValueError, KeyError, TypeError) as e:
                self._logger.warning(f"Failed to fetch stock quote: {e}")
                return None
        return None

    def get_mid_price(
        self,
        symbol: str,
        expiry: date,
        strike: float,
        option_type: OptionType,
    ) -> float:
        """Get the mid price for an option.

        Args:
            symbol: Underlying symbol.
            expiry: Option expiry date.
            strike: Strike price.
            option_type: CALL or PUT.

        Returns:
            The mid price.
        """
        quote = self.get_quote(symbol, expiry, strike, option_type)
        return quote.mid
