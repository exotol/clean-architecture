from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import Any


class ILoggingStrategy(ABC):
    """Interface for logging strategy."""

    @abstractmethod
    def log_start(
        self,
        event_name: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        *,
        use_log_args: bool,
        named_args: dict[str, Any] | None = None,
    ) -> Any:
        """Log start of execution.

        If named_args is provided and use_log_args is True, log by param names;
        otherwise use args/kwargs.
        """

    @abstractmethod
    def log_success(
        self,
        event_name: str,
        result: Any,
        context: Any,
        *,
        use_log_result: bool,
    ) -> None:
        """Log successful execution."""

    @abstractmethod
    def log_error(self, event_name: str, exc: Exception, context: Any) -> None:
        """Log error execution."""


class ITracingStrategy(ABC):
    """Interface for tracing strategy."""

    @abstractmethod
    def start_span(self, name: str) -> Any:
        """Start a new span."""

    @abstractmethod
    def end_span(self, span: Any, exc: Exception | None = None) -> None:
        """End the span."""


class IMetricsStrategy(ABC):
    """Interface for metrics strategy."""

    @abstractmethod
    def record_request(
        self,
        event_name: str,
        duration: float,
        status: str,
        error_type: str | None = None,
    ) -> None:
        """Record request metrics."""

    @abstractmethod
    def record_sla(
        self,
        event_name: str,
        duration: float,
        *,
        success: bool,
    ) -> None:
        """Record SLA metrics (latency + success/error for error rate)."""
