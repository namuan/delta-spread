from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from delta_spread.domain.models import OptionType
from delta_spread.services.async_quote_service import AsyncQuoteService
from delta_spread.services.workers.base import WorkerResult
from delta_spread.services.workers.manager import WorkerManager
from delta_spread.services.workers.options_worker import (
    ChainResult,
    ExpiriesResult,
    QuoteResult,
    StockQuoteResult,
    StrikesResult,
)
from mocks.options_data_mock import MockOptionsDataService

if TYPE_CHECKING:
    from collections.abc import Callable


class FakeWorkerManager(WorkerManager):
    def __init__(self) -> None:
        super().__init__()
        self.submitted: dict[str, Callable[[WorkerResult[object]], None]] = {}
        self.cancelled: list[str] = []
        self.cancel_all_called = False

    def submit(
        self,
        worker,
        *,
        on_complete: Callable[[WorkerResult[object]], None] | None = None,
    ) -> str:
        if on_complete is not None:
            self.submitted[worker.request_id] = on_complete
        return worker.request_id

    def cancel(self, request_id: str) -> bool:
        self.cancelled.append(request_id)
        return True

    def cancel_all(self) -> int:
        self.cancel_all_called = True
        return len(self.submitted)


def test_async_quote_service_expiries_flow_and_cancel_previous() -> None:
    mgr = FakeWorkerManager()
    svc = AsyncQuoteService(
        MockOptionsDataService(today=date(2025, 11, 20)),
        worker_manager=mgr,
    )

    loading: list[tuple[str, str]] = []
    expiries_loaded: list[list[date]] = []

    svc.loading_started.connect(lambda op: loading.append(("start", op)))
    svc.loading_finished.connect(lambda op: loading.append(("end", op)))
    svc.expiries_loaded.connect(expiries_loaded.append)

    req1 = svc.fetch_expiries()
    req2 = svc.fetch_expiries()

    assert mgr.cancelled == [req1]
    assert svc.is_loading is True

    callback = mgr.submitted[req2]
    callback(
        WorkerResult(
            data=ExpiriesResult([date(2026, 1, 17)]),
            error=None,
            request_id=req2,
        )
    )

    assert svc.is_loading is False
    assert expiries_loaded == [[date(2026, 1, 17)]]
    assert loading == [
        ("start", "expiries"),
        ("start", "expiries"),
        ("end", "expiries"),
    ]


def test_async_quote_service_error_paths_clear_pending() -> None:
    mgr = FakeWorkerManager()
    svc = AsyncQuoteService(
        MockOptionsDataService(today=date(2025, 11, 20)),
        worker_manager=mgr,
    )

    errors: list[str] = []
    finished: list[str] = []
    svc.error_occurred.connect(lambda request_id, _exc: errors.append(request_id))
    svc.loading_finished.connect(finished.append)

    expiry = svc.data_service.get_expiries()[0]

    req = svc.fetch_quote("SPX", expiry, 6600.0, OptionType.CALL)
    mgr.submitted[req](WorkerResult(data=None, error=RuntimeError("x"), request_id=req))

    assert errors == [req]
    assert finished == ["quote"]
    assert svc.is_loading is False


def test_async_quote_service_strikes_chain_and_stock_quote_success() -> None:
    mgr = FakeWorkerManager()
    data = MockOptionsDataService(today=date(2025, 11, 20))
    svc = AsyncQuoteService(data, worker_manager=mgr)

    strikes_loaded: list[tuple[str, date, list[float]]] = []
    chain_loaded: list[tuple[str, date, int]] = []
    stock_loaded: list[tuple[str, object]] = []

    svc.strikes_loaded.connect(
        lambda sym, exp, strikes: strikes_loaded.append((sym, exp, strikes))
    )
    svc.chain_loaded.connect(
        lambda sym, exp, chain: chain_loaded.append((sym, exp, len(chain)))
    )
    svc.stock_quote_loaded.connect(lambda sym, quote: stock_loaded.append((sym, quote)))

    expiry = data.get_expiries()[0]

    req_strikes = svc.fetch_strikes("SPX", expiry)
    mgr.submitted[req_strikes](
        WorkerResult(
            data=StrikesResult(symbol="SPX", expiry=expiry, strikes=[1.0, 2.0]),
            error=None,
            request_id=req_strikes,
        )
    )

    req_chain = svc.fetch_chain("SPX", expiry)
    mgr.submitted[req_chain](
        WorkerResult(
            data=ChainResult(symbol="SPX", expiry=expiry, chain=[]),
            error=None,
            request_id=req_chain,
        )
    )

    req_stock = svc.fetch_stock_quote("SPX")
    mgr.submitted[req_stock](
        WorkerResult(
            data=StockQuoteResult(symbol="SPX", quote=None),
            error=None,
            request_id=req_stock,
        )
    )

    assert strikes_loaded == [("SPX", expiry, [1.0, 2.0])]
    assert chain_loaded == [("SPX", expiry, 0)]
    assert stock_loaded == [("SPX", None)]


def test_async_quote_service_quote_success_emits() -> None:
    mgr = FakeWorkerManager()
    data = MockOptionsDataService(today=date(2025, 11, 20))
    svc = AsyncQuoteService(data, worker_manager=mgr)

    quotes: list[tuple[str, date, float, object, object]] = []
    svc.quote_loaded.connect(
        lambda sym, exp, strike, t, q: quotes.append((sym, exp, strike, t, q))
    )

    expiry = data.get_expiries()[0]
    req = svc.fetch_quote("SPX", expiry, 6600.0, OptionType.CALL)

    quote = data.get_quote("SPX", expiry, 6600.0, OptionType.CALL)
    mgr.submitted[req](
        WorkerResult(
            data=QuoteResult(
                symbol="SPX",
                expiry=expiry,
                strike=6600.0,
                option_type=OptionType.CALL,
                quote=quote,
            ),
            error=None,
            request_id=req,
        )
    )

    assert quotes and quotes[0][0] == "SPX"


def test_async_quote_service_cancel_all_clears_tracking() -> None:
    mgr = FakeWorkerManager()
    data = MockOptionsDataService(today=date(2025, 11, 20))
    svc = AsyncQuoteService(data, worker_manager=mgr)

    expiry = data.get_expiries()[0]
    _ = svc.fetch_quote("SPX", expiry, 6600.0, OptionType.CALL)
    _ = svc.fetch_chain("SPX", expiry)

    assert svc.is_loading is True

    svc.cancel_all()

    assert mgr.cancel_all_called is True
    assert svc.is_loading is False
