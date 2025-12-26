"""Workers for options data API calls."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, override
from uuid import uuid4

from .base import BaseWorker

if TYPE_CHECKING:
    from datetime import date

    from delta_spread.data.options_data import OptionsDataService
    from delta_spread.data.tradier_data import StockQuote
    from delta_spread.domain.models import OptionQuote, OptionType


@dataclass(frozen=True)
class ExpiriesResult:
    """Result for expiries fetch."""

    expiries: list[date]


@dataclass(frozen=True)
class StrikesResult:
    """Result for strikes fetch."""

    symbol: str
    expiry: date
    strikes: list[float]


@dataclass(frozen=True)
class ChainResult:
    """Result for options chain fetch."""

    symbol: str
    expiry: date
    chain: list[OptionQuote]


@dataclass(frozen=True)
class QuoteRequest:
    """Request parameters for fetching a quote."""

    symbol: str
    expiry: date
    strike: float
    option_type: OptionType


@dataclass(frozen=True)
class QuoteResult:
    """Result for quote fetch."""

    symbol: str
    expiry: date
    strike: float
    option_type: OptionType
    quote: OptionQuote


@dataclass(frozen=True)
class StockQuoteResult:
    """Result for stock quote fetch."""

    symbol: str
    quote: StockQuote | None


class FetchExpiriesWorker(BaseWorker):
    """Worker to fetch available expiry dates."""

    def __init__(
        self,
        data_service: OptionsDataService,
        request_id: str | None = None,
    ) -> None:
        """Initialize the worker.

        Args:
            data_service: The options data service.
            request_id: Optional request ID (auto-generated if not provided).
        """
        super().__init__(request_id or str(uuid4()))
        self._data_service = data_service

    @override
    def execute(self) -> ExpiriesResult:
        """Fetch expiries from the data service."""
        expiries = self._data_service.get_expiries()
        return ExpiriesResult(expiries=list(expiries))


class FetchStrikesWorker(BaseWorker):
    """Worker to fetch strikes for an expiry."""

    def __init__(
        self,
        data_service: OptionsDataService,
        symbol: str,
        expiry: date,
        request_id: str | None = None,
    ) -> None:
        """Initialize the worker.

        Args:
            data_service: The options data service.
            symbol: Underlying symbol.
            expiry: Expiry date.
            request_id: Optional request ID (auto-generated if not provided).
        """
        super().__init__(request_id or str(uuid4()))
        self._data_service = data_service
        self._symbol = symbol
        self._expiry = expiry

    @override
    def execute(self) -> StrikesResult:
        """Fetch strikes from the data service."""
        strikes = self._data_service.get_strikes(self._symbol, self._expiry)
        return StrikesResult(
            symbol=self._symbol,
            expiry=self._expiry,
            strikes=list(strikes),
        )


class FetchChainWorker(BaseWorker):
    """Worker to fetch the full options chain for an expiry."""

    def __init__(
        self,
        data_service: OptionsDataService,
        symbol: str,
        expiry: date,
        request_id: str | None = None,
    ) -> None:
        """Initialize the worker.

        Args:
            data_service: The options data service.
            symbol: Underlying symbol.
            expiry: Expiry date.
            request_id: Optional request ID (auto-generated if not provided).
        """
        super().__init__(request_id or str(uuid4()))
        self._data_service = data_service
        self._symbol = symbol
        self._expiry = expiry

    @override
    def execute(self) -> ChainResult:
        """Fetch options chain from the data service."""
        chain = self._data_service.get_chain(self._symbol, self._expiry)
        return ChainResult(
            symbol=self._symbol,
            expiry=self._expiry,
            chain=list(chain),
        )


class FetchQuoteWorker(BaseWorker):
    """Worker to fetch a single option quote."""

    def __init__(
        self,
        data_service: OptionsDataService,
        request: QuoteRequest,
        request_id: str | None = None,
    ) -> None:
        """Initialize the worker.

        Args:
            data_service: The options data service.
            request: Quote request parameters.
            request_id: Optional request ID (auto-generated if not provided).
        """
        super().__init__(request_id or str(uuid4()))
        self._data_service = data_service
        self._request = request

    @override
    def execute(self) -> QuoteResult:
        """Fetch quote from the data service."""
        req = self._request
        quote = self._data_service.get_quote(
            req.symbol,
            req.expiry,
            req.strike,
            req.option_type,
        )
        return QuoteResult(
            symbol=req.symbol,
            expiry=req.expiry,
            strike=req.strike,
            option_type=req.option_type,
            quote=quote,
        )


class FetchStockQuoteWorker(BaseWorker):
    """Worker to fetch stock quote."""

    def __init__(
        self,
        data_service: OptionsDataService,
        symbol: str,
        request_id: str | None = None,
    ) -> None:
        """Initialize the worker.

        Args:
            data_service: The options data service.
            symbol: Stock symbol.
            request_id: Optional request ID (auto-generated if not provided).
        """
        super().__init__(request_id or str(uuid4()))
        self._data_service = data_service
        self._symbol = symbol

    @override
    def execute(self) -> StockQuoteResult:
        """Fetch stock quote from the data service."""
        # Import here to avoid circular imports
        from delta_spread.data.tradier_data import (  # noqa: PLC0415
            TradierOptionsDataService,
        )

        if isinstance(self._data_service, TradierOptionsDataService):
            quote = self._data_service.get_stock_quote()
        else:
            quote = None

        return StockQuoteResult(symbol=self._symbol, quote=quote)
