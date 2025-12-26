"""Async wrapper for QuoteService with background execution."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt6.QtCore import QObject, pyqtSignal

from .workers.manager import WorkerManager
from .workers.options_worker import (
    ChainResult,
    ExpiriesResult,
    FetchChainWorker,
    FetchExpiriesWorker,
    FetchQuoteWorker,
    FetchStockQuoteWorker,
    FetchStrikesWorker,
    QuoteRequest,
    QuoteResult,
    StockQuoteResult,
    StrikesResult,
)

if TYPE_CHECKING:
    from datetime import date

    from ..data.options_data import OptionsDataService
    from ..domain.models import OptionType
    from .workers.base import WorkerResult


logger = logging.getLogger(__name__)


class AsyncQuoteService(QObject):
    """Async version of QuoteService using background workers.

    This service wraps the synchronous OptionsDataService and executes
    all calls in background threads, emitting signals when complete.
    """

    # Signals for results
    expiries_loaded = pyqtSignal(list)  # list[date]
    strikes_loaded = pyqtSignal(str, object, list)  # symbol, expiry, list[float]
    chain_loaded = pyqtSignal(str, object, list)  # symbol, expiry, list[OptionQuote]
    quote_loaded = pyqtSignal(
        str, object, float, object, object
    )  # symbol, expiry, strike, type, quote
    stock_quote_loaded = pyqtSignal(str, object)  # symbol, StockQuote | None
    error_occurred = pyqtSignal(str, Exception)  # request_id, exception

    # Loading state signals
    loading_started = pyqtSignal(str)  # operation type
    loading_finished = pyqtSignal(str)  # operation type

    def __init__(
        self,
        data_service: OptionsDataService,
        worker_manager: WorkerManager | None = None,
    ) -> None:
        """Initialize the async quote service.

        Args:
            data_service: The underlying data service.
            worker_manager: Optional worker manager (creates one if not provided).
        """
        super().__init__()
        self._data_service = data_service
        self._worker_manager = worker_manager or WorkerManager()

        # Pending request tracking
        self._pending_expiries: str | None = None
        self._pending_strikes: dict[str, tuple[str, date]] = {}
        self._pending_chains: dict[str, tuple[str, date]] = {}
        self._pending_quotes: dict[str, tuple[str, date, float, OptionType]] = {}
        self._pending_stock_quotes: dict[str, str] = {}

    @property
    def data_service(self) -> OptionsDataService:
        """Get the underlying data service."""
        return self._data_service

    @data_service.setter
    def data_service(self, value: OptionsDataService) -> None:
        """Set the underlying data service."""
        self._data_service = value

    @property
    def is_loading(self) -> bool:
        """Check if any requests are in progress."""
        return (
            self._pending_expiries is not None
            or bool(self._pending_strikes)
            or bool(self._pending_chains)
            or bool(self._pending_quotes)
            or bool(self._pending_stock_quotes)
        )

    def fetch_expiries(self) -> str:
        """Fetch expiries asynchronously.

        Returns:
            Request ID for tracking.
        """
        # Cancel any pending expiries request
        if self._pending_expiries is not None:
            self._worker_manager.cancel(self._pending_expiries)

        worker = FetchExpiriesWorker(self._data_service)
        self._pending_expiries = worker.request_id

        self.loading_started.emit("expiries")

        return self._worker_manager.submit(
            worker,
            on_complete=self._on_expiries_complete,
        )

    def fetch_strikes(self, symbol: str, expiry: date) -> str:
        """Fetch strikes asynchronously.

        Args:
            symbol: Underlying symbol.
            expiry: Expiry date.

        Returns:
            Request ID for tracking.
        """
        worker = FetchStrikesWorker(self._data_service, symbol, expiry)
        self._pending_strikes[worker.request_id] = (symbol, expiry)

        self.loading_started.emit("strikes")

        return self._worker_manager.submit(
            worker,
            on_complete=self._on_strikes_complete,
        )

    def fetch_chain(self, symbol: str, expiry: date) -> str:
        """Fetch full options chain asynchronously.

        Args:
            symbol: Underlying symbol.
            expiry: Expiry date.

        Returns:
            Request ID for tracking.
        """
        worker = FetchChainWorker(self._data_service, symbol, expiry)
        self._pending_chains[worker.request_id] = (symbol, expiry)

        self.loading_started.emit("chain")

        return self._worker_manager.submit(
            worker,
            on_complete=self._on_chain_complete,
        )

    def fetch_quote(
        self,
        symbol: str,
        expiry: date,
        strike: float,
        option_type: OptionType,
    ) -> str:
        """Fetch an option quote asynchronously.

        Args:
            symbol: Underlying symbol.
            expiry: Expiry date.
            strike: Strike price.
            option_type: CALL or PUT.

        Returns:
            Request ID for tracking.
        """
        request = QuoteRequest(
            symbol=symbol,
            expiry=expiry,
            strike=strike,
            option_type=option_type,
        )
        worker = FetchQuoteWorker(self._data_service, request)
        self._pending_quotes[worker.request_id] = (symbol, expiry, strike, option_type)

        self.loading_started.emit("quote")

        return self._worker_manager.submit(
            worker,
            on_complete=self._on_quote_complete,
        )

    def fetch_stock_quote(self, symbol: str) -> str:
        """Fetch stock quote asynchronously.

        Args:
            symbol: Stock symbol.

        Returns:
            Request ID for tracking.
        """
        worker = FetchStockQuoteWorker(self._data_service, symbol)
        self._pending_stock_quotes[worker.request_id] = symbol

        self.loading_started.emit("stock_quote")

        return self._worker_manager.submit(
            worker,
            on_complete=self._on_stock_quote_complete,
        )

    def cancel_all(self) -> None:
        """Cancel all pending requests."""
        self._worker_manager.cancel_all()
        self._pending_expiries = None
        self._pending_strikes.clear()
        self._pending_chains.clear()
        self._pending_quotes.clear()
        self._pending_stock_quotes.clear()

    def _on_expiries_complete(self, result: WorkerResult[object]) -> None:
        """Handle expiries fetch completion."""
        self._pending_expiries = None
        self.loading_finished.emit("expiries")

        if result.error is not None:
            logger.error("Failed to fetch expiries: %s", result.error)
            self.error_occurred.emit(result.request_id, result.error)
            return

        if isinstance(result.data, ExpiriesResult):
            self.expiries_loaded.emit(result.data.expiries)

    def _on_strikes_complete(self, result: WorkerResult[object]) -> None:
        """Handle strikes fetch completion."""
        self._pending_strikes.pop(result.request_id, None)
        self.loading_finished.emit("strikes")

        if result.error is not None:
            logger.error("Failed to fetch strikes: %s", result.error)
            self.error_occurred.emit(result.request_id, result.error)
            return

        if isinstance(result.data, StrikesResult):
            self.strikes_loaded.emit(
                result.data.symbol,
                result.data.expiry,
                result.data.strikes,
            )

    def _on_chain_complete(self, result: WorkerResult[object]) -> None:
        """Handle chain fetch completion."""
        self._pending_chains.pop(result.request_id, None)
        self.loading_finished.emit("chain")

        if result.error is not None:
            logger.error("Failed to fetch chain: %s", result.error)
            self.error_occurred.emit(result.request_id, result.error)
            return

        if isinstance(result.data, ChainResult):
            self.chain_loaded.emit(
                result.data.symbol,
                result.data.expiry,
                result.data.chain,
            )

    def _on_quote_complete(self, result: WorkerResult[object]) -> None:
        """Handle quote fetch completion."""
        self._pending_quotes.pop(result.request_id, None)
        self.loading_finished.emit("quote")

        if result.error is not None:
            logger.error("Failed to fetch quote: %s", result.error)
            self.error_occurred.emit(result.request_id, result.error)
            return

        if isinstance(result.data, QuoteResult):
            self.quote_loaded.emit(
                result.data.symbol,
                result.data.expiry,
                result.data.strike,
                result.data.option_type,
                result.data.quote,
            )

    def _on_stock_quote_complete(self, result: WorkerResult[object]) -> None:
        """Handle stock quote fetch completion."""
        self._pending_stock_quotes.pop(result.request_id, None)
        self.loading_finished.emit("stock_quote")

        if result.error is not None:
            logger.error("Failed to fetch stock quote: %s", result.error)
            self.error_occurred.emit(result.request_id, result.error)
            return

        if isinstance(result.data, StockQuoteResult):
            self.stock_quote_loaded.emit(result.data.symbol, result.data.quote)
