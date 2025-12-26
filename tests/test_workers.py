from __future__ import annotations

from datetime import date

from delta_spread.domain.models import OptionType
from delta_spread.services.workers.base import BaseWorker, WorkerResult
from delta_spread.services.workers.manager import WorkerManager
from delta_spread.services.workers.options_worker import (
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
from mocks.options_data_mock import MockOptionsDataService


def test_worker_result_is_success() -> None:
    assert WorkerResult(data=1, error=None, request_id="x").is_success is True
    assert WorkerResult(data=None, error=None, request_id="x").is_success is False
    assert (
        WorkerResult(data=1, error=ValueError("x"), request_id="x").is_success is False
    )


def test_base_worker_run_cancelled_before_start() -> None:
    class CancelledWorker(BaseWorker):
        def execute(self) -> object:  # pragma: no cover
            raise AssertionError("should not execute")

    worker = CancelledWorker("req")
    cancelled: list[str] = []
    worker.signals.cancelled.connect(cancelled.append)

    worker.cancel()
    worker.run()

    assert cancelled == ["req"]


def test_base_worker_run_success_error_and_cancel_after_execute() -> None:
    class OkWorker(BaseWorker):
        def execute(self) -> object:
            return 123

    class ErrorWorker(BaseWorker):
        def execute(self) -> object:
            raise ValueError("boom")

    class CancelAfterExecuteWorker(BaseWorker):
        def execute(self) -> object:
            self.cancel()
            return 456

    ok = OkWorker("ok")
    finished: list[WorkerResult[object]] = []
    ok.signals.finished.connect(finished.append)

    ok.run()
    assert len(finished) == 1
    assert finished[0].is_success is True
    assert finished[0].data == 123

    err = ErrorWorker("err")
    finished_err: list[WorkerResult[object]] = []
    errors: list[tuple[str, Exception]] = []
    err.signals.finished.connect(finished_err.append)
    err.signals.error.connect(lambda request_id, exc: errors.append((request_id, exc)))

    err.run()
    assert len(finished_err) == 1
    assert finished_err[0].data is None
    assert isinstance(finished_err[0].error, ValueError)
    assert errors and errors[0][0] == "err"

    cancelled = CancelAfterExecuteWorker("cancel")
    cancelled_ids: list[str] = []
    cancelled.signals.cancelled.connect(cancelled_ids.append)

    cancelled.run()
    assert cancelled_ids == ["cancel"]


def test_options_workers_execute_mapping() -> None:
    svc = MockOptionsDataService(today=date(2025, 11, 20))
    expiry = svc.get_expiries()[0]

    exp_worker = FetchExpiriesWorker(svc, request_id="exp")
    exp_result = exp_worker.execute()
    assert isinstance(exp_result, ExpiriesResult)

    strikes_worker = FetchStrikesWorker(
        svc, symbol="SPX", expiry=expiry, request_id="stk"
    )
    strikes_result = strikes_worker.execute()
    assert isinstance(strikes_result, StrikesResult)
    assert strikes_result.symbol == "SPX"

    chain_worker = FetchChainWorker(svc, symbol="SPX", expiry=expiry, request_id="chn")
    chain_result = chain_worker.execute()
    assert isinstance(chain_result, ChainResult)
    assert chain_result.symbol == "SPX"

    req = QuoteRequest(
        symbol="SPX",
        expiry=expiry,
        strike=strikes_result.strikes[0],
        option_type=OptionType.CALL,
    )
    quote_worker = FetchQuoteWorker(svc, req, request_id="q")
    quote_result = quote_worker.execute()
    assert isinstance(quote_result, QuoteResult)
    assert quote_result.option_type is OptionType.CALL


def test_fetch_stock_quote_worker_non_tradier_returns_none() -> None:
    svc = MockOptionsDataService(today=date(2025, 11, 20))
    worker = FetchStockQuoteWorker(svc, symbol="SPX", request_id="sq")
    result = worker.execute()

    assert isinstance(result, StockQuoteResult)
    assert result.symbol == "SPX"
    assert result.quote is None


def test_worker_manager_submit_and_callbacks(monkeypatch) -> None:
    class ImmediateThreadPool:
        def setMaxThreadCount(self, _n: int) -> None:
            return None

        def activeThreadCount(self) -> int:
            return 0

        def start(self, runnable) -> None:
            runnable.run()

        def waitForDone(self, _timeout_ms: int) -> bool:
            return True

    from PyQt6 import QtCore

    monkeypatch.setattr(
        QtCore.QThreadPool, "globalInstance", lambda: ImmediateThreadPool()
    )

    manager = WorkerManager()

    class OkWorker(BaseWorker):
        def execute(self) -> object:
            return "done"

    worker = OkWorker("req")

    callbacks: list[WorkerResult[object]] = []
    manager.submit(worker, on_complete=callbacks.append)

    assert manager.active_count == 0
    assert len(callbacks) == 1
    assert callbacks[0].is_success is True

    assert manager.wait_for_done(1) is True


def test_worker_manager_cancel_paths(monkeypatch) -> None:
    class ImmediateThreadPool:
        def setMaxThreadCount(self, _n: int) -> None:
            return None

        def activeThreadCount(self) -> int:
            return 0

        def start(self, runnable) -> None:
            runnable.run()

        def waitForDone(self, _timeout_ms: int) -> bool:
            return True

    from PyQt6 import QtCore

    monkeypatch.setattr(
        QtCore.QThreadPool, "globalInstance", lambda: ImmediateThreadPool()
    )

    manager = WorkerManager()

    class SlowWorker(BaseWorker):
        def execute(self) -> object:
            return "x"

    worker = SlowWorker("req")
    manager._active_workers["req"] = worker

    assert manager.cancel("missing") is False
    assert manager.cancel("req") is True
    assert worker.is_cancelled is True

    manager._active_workers["req2"] = SlowWorker("req2")
    assert manager.cancel_all() == 2


def test_worker_manager_callback_exception_does_not_escape(monkeypatch) -> None:
    class ImmediateThreadPool:
        def setMaxThreadCount(self, _n: int) -> None:
            return None

        def activeThreadCount(self) -> int:
            return 0

        def start(self, runnable) -> None:
            runnable.run()

        def waitForDone(self, _timeout_ms: int) -> bool:
            return True

    from PyQt6 import QtCore

    monkeypatch.setattr(
        QtCore.QThreadPool, "globalInstance", lambda: ImmediateThreadPool()
    )

    manager = WorkerManager()

    def bad_callback(_result: WorkerResult[object]) -> None:
        raise RuntimeError("oops")

    class OkWorker(BaseWorker):
        def execute(self) -> object:
            return 1

    worker = OkWorker("req")
    manager.submit(worker, on_complete=bad_callback)

    assert manager.active_count == 0
