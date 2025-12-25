"""Tradier Options Data Service implementation."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import TYPE_CHECKING, Any, TypedDict

from dotmap import DotMap  # type: ignore[import-untyped]
import requests

from delta_spread.domain.models import OptionQuote

if TYPE_CHECKING:
    from datetime import date

    from delta_spread.domain.models import OptionType

logger = logging.getLogger(__name__)


class StockQuote(TypedDict):
    """Stock quote data structure."""

    last: float
    change: float
    change_percentage: float
    prevclose: float


class TradierOptionsDataService:
    """Real options data service using Tradier API."""

    # Constants for option parsing
    STRIKE_TOLERANCE = 0.01  # Tolerance for comparing strike prices
    OPTION_SYMBOL_STRIKE_LENGTH = 8  # Expected length of strike in option symbol

    def __init__(self, symbol: str, base_url: str, token: str) -> None:
        """Initialize Tradier data service.

        Args:
            symbol: The underlying symbol (e.g., "SPY", "AAPL")
            base_url: Tradier API base URL
            token: Tradier API authentication token
        """
        super().__init__()
        self.symbol = symbol.upper()
        self.base_url = base_url.rstrip("/")
        self.token = token
        self._expiries_cache: list[date] | None = None
        self._chain_cache: dict[tuple[str, date], list[OptionQuote]] = {}

    def _get_data(self, path: str, params: dict[str, Any]) -> DotMap:  # type: ignore[misc]
        """Make authenticated request to Tradier API.

        Args:
            path: API endpoint path
            params: Query parameters

        Returns:
            DotMap response object

        Raises:
            requests.HTTPError: If API request fails
        """
        url = f"{self.base_url}/{path.lstrip("/")}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        }

        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            return DotMap(response.json())  # type: ignore[no-any-return]
        except requests.RequestException as e:
            logger.error(f"Tradier API request failed: {e}")
            raise

    def get_stock_quote(self) -> StockQuote | None:
        """Fetch stock quote for the symbol.

        Returns:
            Dictionary with quote data or None if request fails
        """
        path = "/markets/quotes"
        params = {"symbols": self.symbol}

        try:
            response = self._get_data(path, params)

            if not hasattr(response, "quotes") or not response.quotes:  # type: ignore[attr-defined]
                logger.warning(f"No quote found for {self.symbol}")
                return None

            quote = response.quotes.get("quote", {})  # type: ignore[attr-defined]
            if isinstance(quote, list) and quote:
                quote = quote[0]  # type: ignore[assignment]

            return {
                "last": float(quote.get("last", 0) or 0),  # type: ignore[union-attr]
                "change": float(quote.get("change", 0) or 0),  # type: ignore[union-attr]
                "change_percentage": float(quote.get("change_percentage", 0) or 0),  # type: ignore[union-attr]
                "prevclose": float(quote.get("prevclose", 0) or 0),  # type: ignore[union-attr]
            }
        except (requests.RequestException, KeyError, ValueError, AttributeError) as e:
            logger.error(f"Failed to fetch stock quote: {e}")
            return None

    def get_expiries(self) -> list[date]:
        """Fetch available expiration dates for the symbol.

        Returns:
            List of expiration dates sorted chronologically
        """
        if self._expiries_cache is not None:
            return self._expiries_cache

        path = "/markets/options/expirations"
        params = {
            "symbol": self.symbol,
            "includeAllRoots": "true",
        }

        try:
            response = self._get_data(path, params)

            if not hasattr(response, "expirations") or not response.expirations:  # type: ignore[misc]
                logger.warning(f"No expirations found for {self.symbol}")
                return []

            # Parse dates from the response
            dates_list = response.expirations.get("date", [])  # type: ignore[attr-defined,misc]
            if isinstance(dates_list, str):
                dates_list = [dates_list]

            expiries = [datetime.strptime(d, "%Y-%m-%d").date() for d in dates_list]  # type: ignore[misc,arg-type,union-attr]

            self._expiries_cache = sorted(expiries)
            logger.info(
                f"Fetched {len(self._expiries_cache)} expiries for {self.symbol}"
            )
            return self._expiries_cache

        except (requests.RequestException, KeyError, ValueError, AttributeError) as e:
            logger.error(f"Failed to fetch expiries: {e}")
            return []

    def get_strikes(self, symbol: str, expiry: date) -> list[float]:
        """Get available strikes for a given expiration.

        Args:
            symbol: Underlying symbol
            expiry: Expiration date

        Returns:
            Sorted list of strike prices
        """
        self.get_chain(symbol, expiry)
        # Extract unique strikes from the chain
        # Extract unique strikes from the raw chain data
        raw_chain = self._get_raw_chain(symbol, expiry)
        strike_set: set[float] = set()
        for opt_data in raw_chain:  # type: ignore[attr-defined]
            strike_val = opt_data.get("strike", 0)  # type: ignore[attr-defined]
            if strike_val:
                strike_set.add(float(strike_val))  # type: ignore[arg-type]
        return sorted(strike_set)

    def get_chain(self, symbol: str, expiry: date) -> list[OptionQuote]:
        """Fetch complete option chain for symbol and expiration.

        Args:
            symbol: Underlying symbol
            expiry: Expiration date

        Returns:
            List of OptionQuote objects for all strikes and types
        """
        cache_key = (symbol.upper(), expiry)
        if cache_key in self._chain_cache:
            return self._chain_cache[cache_key]

        raw_chain = self._get_raw_chain(symbol, expiry)
        quotes: list[OptionQuote] = []

        for option_data in raw_chain:  # type: ignore[attr-defined]
            try:
                quote = self._parse_option_quote(option_data)  # type: ignore[arg-type]
                if quote:
                    quotes.append(quote)
            except (KeyError, ValueError, TypeError) as e:
                logger.warning(f"Failed to parse option: {e}")
                continue

        self._chain_cache[cache_key] = quotes
        logger.info(f"Fetched {len(quotes)} options for {symbol} {expiry}")
        return quotes

    def _get_raw_chain(self, symbol: str, expiry: date) -> list[Any]:  # type: ignore[misc]
        """Fetch raw option chain data from Tradier.

        Args:
            symbol: Underlying symbol
            expiry: Expiration date

        Returns:
            List of raw option data dictionaries
        """
        path = "/markets/options/chains"
        params = {
            "symbol": symbol.upper(),
            "expiration": expiry.strftime("%Y-%m-%d"),
            "greeks": "true",
        }

        try:
            response = self._get_data(path, params)

            if not hasattr(response, "options") or not response.options:  # type: ignore[attr-defined]
                logger.warning(f"No options found for {symbol} {expiry}")
                return []

            options = response.options.get("option", [])  # type: ignore[attr-defined]
            if isinstance(options, dict):
                options = [options]  # type: ignore[assignment]

            return options  # type: ignore[return-value]

        except (requests.RequestException, KeyError, ValueError, AttributeError) as e:
            logger.error(f"Failed to fetch chain: {e}")
            return []

    def get_quote(
        self, symbol: str, expiry: date, strike: float, type: OptionType
    ) -> OptionQuote:
        """Get quote for specific option contract.

        Args:
            symbol: Underlying symbol
            expiry: Expiration date
            strike: Strike price
            type: Option type (CALL or PUT)

        Returns:
            OptionQuote for the specified contract

        Raises:
            ValueError: If option not found
        """
        self.get_chain(symbol, expiry)

        for quote_data in self._get_raw_chain(symbol, expiry):  # type: ignore[attr-defined]
            opt_strike = quote_data.get("strike", 0)  # type: ignore[attr-defined]
            opt_type = quote_data.get("option_type", "").upper()  # type: ignore[attr-defined,union-attr]

            if (
                abs(opt_strike - strike) < self.STRIKE_TOLERANCE  # type: ignore[arg-type]
                and opt_type == type.value
            ):
                quote = self._parse_option_quote(quote_data)  # type: ignore[arg-type]
                if quote:
                    return quote

        # If not found in current data, return a default quote
        raise ValueError(f"Option not found: {symbol} {expiry} {strike} {type.value}")

    @staticmethod
    def _parse_option_quote(option_data: dict[str, object]) -> OptionQuote | None:
        """Parse raw option data into OptionQuote.

        Args:
            option_data: Raw option data from Tradier

        Returns:
            OptionQuote object or None if parsing fails
        """
        try:
            bid = float(option_data.get("bid", 0) or 0)  # type: ignore[arg-type]
            ask = float(option_data.get("ask", 0) or 0)  # type: ignore[arg-type]

            # Calculate mid price
            mid = round((bid + ask) / 2, 2) if bid > 0 and ask > 0 else 0.0

            # Get implied volatility from greeks
            iv = 0.0
            if hasattr(option_data, "greeks") and option_data.greeks:  # type: ignore[attr-defined]
                iv = float(option_data.greeks.get("mid_iv", 0) or 0)  # type: ignore[attr-defined]

            # Ensure valid price relationship
            if bid > ask > 0:
                bid, ask = ask, bid

            return OptionQuote(
                bid=round(bid, 2),
                ask=round(ask, 2),
                mid=mid,
                iv=round(iv, 4),
                last_updated=datetime.now(),
            )
        except (ValueError, AttributeError, KeyError) as e:
            logger.warning(f"Failed to parse option quote: {e}")
            return None

    @staticmethod
    def _extract_strike_from_symbol(option_symbol: str) -> float:
        """Extract strike price from option symbol.

        Tradier option symbols follow format: SYMBOL+YYMMDD[C|P]STRIKE
        Example: SPY250117C00600000 = SPY Jan 17, 2025 $600 Call

        Args:
            option_symbol: Tradier option symbol

        Returns:
            Strike price as float
        """
        try:
            # Find the C or P indicator (last occurrence in case symbol has C or P)
            c_pos = option_symbol.rfind("C")
            p_pos = option_symbol.rfind("P")

            # Use whichever is found (C or P)
            if c_pos > p_pos:
                pos = c_pos
            elif p_pos > c_pos:
                pos = p_pos
            else:
                return 0.0

            # Strike is after C/P, 8 digits representing price * 1000
            strike_str = option_symbol[pos + 1 : pos + 9]
            if (
                len(strike_str) == TradierOptionsDataService.OPTION_SYMBOL_STRIKE_LENGTH
                and strike_str.isdigit()
            ):
                return float(strike_str) / 1000.0
            return 0.0
        except (ValueError, IndexError):
            return 0.0
