from __future__ import annotations

import functools
import inspect
from time import perf_counter
from typing import Any
from typing import ParamSpec
from typing import TYPE_CHECKING
from typing import TypeVar
from typing import cast

from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject

from app.core.events import Events
from app.core.exceptions import BusinessError
from app.core.exceptions import InfrastructureError

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Coroutine

    from app.domain.interfaces.observability import ILoggingStrategy
    from app.domain.interfaces.observability import IMetricsStrategy
    from app.domain.interfaces.observability import ITracingStrategy


# --- Typing ---
P = ParamSpec("P")
R = TypeVar("R")


# --- Strategy Getters (using @inject) ---
@inject
def _get_logging_strategy(
    strategy: ILoggingStrategy = Provide["infra_container.logging_strategy"],
) -> ILoggingStrategy:
    return strategy


@inject
def _get_tracing_strategy(
    strategy: ITracingStrategy = Provide["infra_container.tracing_strategy"],
) -> ITracingStrategy:
    return strategy


@inject
def _get_metrics_strategy(
    strategy: IMetricsStrategy = Provide["infra_container.metrics_strategy"],
) -> IMetricsStrategy:
    return strategy


class _MonitoringHandler:
    """
    Helper class to handle logging and tracing logic for the monitor decorator.
    Delegates to injected strategies.
    """

    def __init__(
        self,
        func: Callable[..., Any],
        event_name: Events | str,
        *,
        reraise: bool = True,
        action_when_exception: Callable[[Exception], Any] | None = None,
        use_log_args: bool = False,
        use_log_result: bool = False,
    ) -> None:
        self.func = func
        if isinstance(event_name, Events):
            self.event_name = event_name.value.code
        else:
            self.event_name = event_name

        self.reraise = reraise
        self.action_when_exception = action_when_exception
        self.use_log_args = use_log_args
        self.use_log_result = use_log_result

        self._logging_strategy: ILoggingStrategy | None = None
        self._tracing_strategy: ITracingStrategy | None = None
        self._metrics_strategy: IMetricsStrategy | None = None

    @property
    def logging_strategy(self) -> ILoggingStrategy:
        if self._logging_strategy is None:
            self._logging_strategy = _get_logging_strategy()
        return self._logging_strategy

    @property
    def tracing_strategy(self) -> ITracingStrategy:
        if self._tracing_strategy is None:
            self._tracing_strategy = _get_tracing_strategy()
        return self._tracing_strategy

    @property
    def metrics_strategy(self) -> IMetricsStrategy:
        if self._metrics_strategy is None:
            self._metrics_strategy = _get_metrics_strategy()
        return self._metrics_strategy

    def log_start(
        self, args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> tuple[float, Any]:
        """Logs start and returns (start_time, log_context)."""
        if hasattr(self.logging_strategy, "use_log_args"):
            self.logging_strategy.use_log_args = self.use_log_args  # type: ignore[attr-defined]

        context = self.logging_strategy.log_start(self.event_name, args, kwargs)
        return perf_counter(), context

    def log_success(self, result: Any, start_time: float, context: Any) -> None:
        duration = perf_counter() - start_time
        self.metrics_strategy.record_request(
            event_name=self.event_name,
            duration=duration,
            status="success",
        )

        if hasattr(self.logging_strategy, "use_log_result"):
            self.logging_strategy.use_log_result = self.use_log_result  # type: ignore[attr-defined]

        self.logging_strategy.log_success(self.event_name, result, context)

    def log_error(self, exc: Exception, start_time: float, context: Any) -> None:
        duration = perf_counter() - start_time
        error_type = _classify_error(exc)
        self.metrics_strategy.record_request(
            event_name=self.event_name,
            duration=duration,
            status="error",
            error_type=error_type,
        )

        self.logging_strategy.log_error(self.event_name, exc, context)

        if self.action_when_exception:
            self._safe_execute_callback(exc)

    def _safe_execute_callback(self, exc: Exception) -> None:
        try:
            if self.action_when_exception:
                self.action_when_exception(exc)
        except Exception:
            pass


def _classify_error(exc: Exception) -> str:
    if isinstance(exc, BusinessError):
        return "business"
    if isinstance(exc, InfrastructureError):
        return "infrastructure"
    return "unknown"


def _async_wrapper(
    func: Callable[P, Coroutine[Any, Any, R]],
    handler: _MonitoringHandler,
) -> Callable[P, Coroutine[Any, Any, R]]:
    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        span = handler.tracing_strategy.start_span(handler.event_name)
        with span:
            start_time, context = handler.log_start(args, kwargs)
            try:
                result = await func(*args, **kwargs)
            except Exception as exc:
                handler.log_error(exc, start_time, context)
                if handler.reraise:
                    raise
                return cast("R", None)

            handler.log_success(result, start_time, context)
            return result

    return wrapper


def _sync_wrapper(
    func: Callable[P, R],
    handler: _MonitoringHandler,
) -> Callable[P, R]:
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        span = handler.tracing_strategy.start_span(handler.event_name)
        with span:
            start_time, context = handler.log_start(args, kwargs)
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                handler.log_error(exc, start_time, context)
                if handler.reraise:
                    raise
                return cast("R", None)

            handler.log_success(result, start_time, context)
            return result

    return wrapper


def monitor(
    event_name: Events | str,
    *,
    reraise: bool = True,
    action_when_exception: Callable[[Exception], Any] | None = None,
    use_log_args: bool = True,
    use_log_result: bool = True,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator factory for monitoring function execution."""

    def decorator(
        func: Callable[P, R] | Callable[P, Coroutine[Any, Any, R]],
    ) -> Callable[P, R] | Callable[P, Coroutine[Any, Any, R]]:
        handler = _MonitoringHandler(
            func,
            event_name=event_name,
            reraise=reraise,
            action_when_exception=action_when_exception,
            use_log_args=use_log_args,
            use_log_result=use_log_result,
        )

        if inspect.iscoroutinefunction(func):
            return cast(
                "Callable[P, Coroutine[Any, Any, R]]",
                _async_wrapper(
                    cast("Callable[P, Coroutine[Any, Any, R]]", func), handler
                ),
            )
        return cast(
            "Callable[P, R]",
            _sync_wrapper(cast("Callable[P, R]", func), handler),
        )

    return cast(
        "Callable[[Callable[P, R] | "
        "Callable[P, Coroutine[Any, Any, R]]], Any]",
        decorator,
    )
