"""Base worker classes for background API operations."""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import override

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal


class WorkerState(Enum):
    """Worker execution state."""

    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    CANCELLED = auto()
    ERROR = auto()


@dataclass(frozen=True)
class WorkerResult[T]:
    """Immutable result container for worker operations."""

    data: T | None
    error: Exception | None
    request_id: str

    @property
    def is_success(self) -> bool:
        """Check if the operation succeeded."""
        return self.error is None and self.data is not None


class WorkerSignals(QObject):
    """Signals for worker communication.

    Qt requires signals to be defined on QObject subclasses.
    We use a separate class to allow QRunnable workers to emit signals.
    """

    # Emitted when work starts
    started = pyqtSignal(str)  # request_id

    # Emitted on successful completion with result
    finished = pyqtSignal(object)  # WorkerResult

    # Emitted on error
    error = pyqtSignal(str, Exception)  # request_id, exception

    # Emitted when cancelled
    cancelled = pyqtSignal(str)  # request_id

    # Progress update (0-100)
    progress = pyqtSignal(str, int)  # request_id, percent


class BaseWorker(QRunnable):
    """Base class for background workers.

    Uses QRunnable for efficient thread pool execution.
    Subclasses implement the `execute()` method.
    """

    def __init__(self, request_id: str) -> None:
        """Initialize the worker.

        Args:
            request_id: Unique identifier for this request.
        """
        super().__init__()
        self.request_id = request_id
        self.signals = WorkerSignals()
        self._is_cancelled = False
        self.setAutoDelete(True)

    @abstractmethod
    def execute(self) -> object:
        """Execute the work. Override in subclasses.

        Returns:
            The result of the operation.

        Raises:
            Exception: If the operation fails.
        """
        ...

    @override
    def run(self) -> None:
        """Run the worker (called by QThreadPool)."""
        if self._is_cancelled:
            self.signals.cancelled.emit(self.request_id)
            return

        self.signals.started.emit(self.request_id)

        try:
            result = self.execute()
            if self._is_cancelled:
                self.signals.cancelled.emit(self.request_id)
                return

            worker_result: WorkerResult[object] = WorkerResult(
                data=result,
                error=None,
                request_id=self.request_id,
            )
            self.signals.finished.emit(worker_result)

        except Exception as e:  # noqa: BLE001
            # Catch all exceptions from user code to emit as errors
            worker_result = WorkerResult(
                data=None,
                error=e,
                request_id=self.request_id,
            )
            self.signals.finished.emit(worker_result)
            self.signals.error.emit(self.request_id, e)

    def cancel(self) -> None:
        """Request cancellation of this worker."""
        self._is_cancelled = True

    @property
    def is_cancelled(self) -> bool:
        """Check if cancellation was requested."""
        return self._is_cancelled
