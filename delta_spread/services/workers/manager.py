"""Worker manager for coordinating background tasks."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from PyQt6.QtCore import QObject, QThreadPool, pyqtSignal

if TYPE_CHECKING:
    from collections.abc import Callable

    from PyQt6.QtCore import QRunnable

    from .base import BaseWorker, WorkerResult

logger = logging.getLogger(__name__)


# Type alias for signal connect method
type SignalConnect = Callable[..., object]


class WorkerManager(QObject):
    """Manages background workers and their lifecycle.

    Provides a centralized interface for:
    - Submitting workers to the thread pool
    - Tracking in-flight requests
    - Cancelling pending work
    - Routing results to callbacks
    """

    # Global signals for monitoring
    worker_started = pyqtSignal(str)  # request_id
    worker_finished = pyqtSignal(object)  # WorkerResult
    worker_error = pyqtSignal(str, Exception)  # request_id, exception
    all_workers_complete = pyqtSignal()

    def __init__(self, max_threads: int | None = None) -> None:
        """Initialize the worker manager.

        Args:
            max_threads: Maximum concurrent threads. Defaults to QThreadPool default.
        """
        super().__init__()
        thread_pool = QThreadPool.globalInstance()
        if thread_pool is None:
            msg = "Failed to get global QThreadPool instance"
            raise RuntimeError(msg)
        self._thread_pool: QThreadPool = thread_pool
        if max_threads is not None:
            self._thread_pool.setMaxThreadCount(max_threads)

        self._active_workers: dict[str, BaseWorker] = {}
        self._callbacks: dict[str, Callable[[WorkerResult[object]], None]] = {}

    @property
    def active_count(self) -> int:
        """Get the number of active workers."""
        return len(self._active_workers)

    @property
    def thread_count(self) -> int:
        """Get the current thread pool thread count."""
        return self._thread_pool.activeThreadCount()

    def submit(
        self,
        worker: BaseWorker,
        *,
        on_complete: Callable[[WorkerResult[object]], None] | None = None,
    ) -> str:
        """Submit a worker for execution.

        Args:
            worker: The worker to execute.
            on_complete: Optional callback when work completes.

        Returns:
            The request ID for tracking.
        """
        request_id = worker.request_id

        # Store worker and callback
        self._active_workers[request_id] = worker
        if on_complete is not None:
            self._callbacks[request_id] = on_complete

        # Connect signals (cast to work around PyQt6 type stub limitations)
        connect_started = cast("SignalConnect", worker.signals.started.connect)
        connect_finished = cast("SignalConnect", worker.signals.finished.connect)
        connect_error = cast("SignalConnect", worker.signals.error.connect)
        connect_cancelled = cast("SignalConnect", worker.signals.cancelled.connect)

        connect_started(self._on_worker_started)
        connect_finished(self._on_worker_finished)
        connect_error(self._on_worker_error)
        connect_cancelled(self._on_worker_cancelled)

        # Start execution (PyQt6 type stubs incomplete for QThreadPool.start)
        self._thread_pool.start(cast("QRunnable", worker))  # pyright: ignore[reportUnknownMemberType]
        logger.debug("Submitted worker %s", request_id)

        return request_id

    def cancel(self, request_id: str) -> bool:
        """Cancel a pending worker.

        Args:
            request_id: The request to cancel.

        Returns:
            True if cancellation was requested, False if not found.
        """
        worker = self._active_workers.get(request_id)
        if worker is not None:
            worker.cancel()
            logger.debug("Requested cancellation for %s", request_id)
            return True
        return False

    def cancel_all(self) -> int:
        """Cancel all pending workers.

        Returns:
            Number of workers cancelled.
        """
        count = 0
        for request_id in list(self._active_workers.keys()):
            if self.cancel(request_id):
                count += 1
        return count

    def wait_for_done(self, timeout_ms: int = -1) -> bool:
        """Wait for all workers to complete.

        Args:
            timeout_ms: Timeout in milliseconds (-1 for infinite).

        Returns:
            True if all workers completed, False on timeout.
        """
        return self._thread_pool.waitForDone(timeout_ms)

    def _on_worker_started(self, request_id: str) -> None:
        """Handle worker started signal."""
        logger.debug("Worker started: %s", request_id)
        self.worker_started.emit(request_id)

    def _on_worker_finished(self, result: WorkerResult[object]) -> None:
        """Handle worker finished signal."""
        request_id = result.request_id
        logger.debug("Worker finished: %s (success=%s)", request_id, result.is_success)

        # Invoke callback if registered
        callback = self._callbacks.pop(request_id, None)
        if callback is not None:
            try:
                callback(result)
            except Exception as e:
                logger.exception("Callback error for %s: %s", request_id, e)

        # Cleanup
        self._active_workers.pop(request_id, None)

        # Emit signals
        self.worker_finished.emit(result)
        if not self._active_workers:
            self.all_workers_complete.emit()

    def _on_worker_error(self, request_id: str, exception: Exception) -> None:
        """Handle worker error signal."""
        logger.error("Worker error %s: %s", request_id, exception)
        self.worker_error.emit(request_id, exception)

    def _on_worker_cancelled(self, request_id: str) -> None:
        """Handle worker cancelled signal."""
        logger.debug("Worker cancelled: %s", request_id)
        self._active_workers.pop(request_id, None)
        self._callbacks.pop(request_id, None)
