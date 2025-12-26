from typing import Any
from typing import Protocol
from typing import runtime_checkable


@runtime_checkable
class ILoggingStrategy(Protocol):
    """Interface for logging strategy."""

    def log_start(
        self,
        event_name: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        *,
        use_log_args: bool = True,
    ) -> Any:
        """Log start of execution."""
        ...

    def log_success(
        self,
        event_name: str,
        result: Any,
        context: Any,
        *,
        use_log_result: bool = True,
    ) -> None:
        """Log successful execution."""
        ...

    def log_error(self, event_name: str, exc: Exception, context: Any) -> None:
        """Log error execution."""
        ...


@runtime_checkable
class ITracingStrategy(Protocol):
    """Interface for tracing strategy."""

    def start_span(self, name: str) -> Any:
        """Start a new span."""
        ...

    def end_span(self, span: Any, exc: Exception | None = None) -> None:
        """End the span."""
        ...


@runtime_checkable
class IMetricsStrategy(Protocol):
    """Interface for metrics strategy."""

    def record_request(
        self,
        event_name: str,
        duration: float,
        status: str,
        error_type: str | None = None,
    ) -> None:
        """Record request metrics."""
        ...
