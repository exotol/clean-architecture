from __future__ import annotations

from dataclasses import dataclass
import functools
import inspect
import logging
from time import perf_counter
from typing import TYPE_CHECKING
from typing import Any
from typing import ParamSpec
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

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _MonitorOptions:
    """Options for monitor behaviour (reraise, callbacks, logging)."""

    reraise: bool = True
    action_when_exception: Callable[..., Any] | None = None
    use_log_args: bool = False
    use_log_result: bool = False


@dataclass(frozen=True)
class _MonitorStrategies:
    """Injected observability strategies for monitor."""

    logging: ILoggingStrategy
    tracing: ITracingStrategy
    metrics: IMetricsStrategy


@inject
def _resolve_monitor_strategies(
    logging_strategy: ILoggingStrategy = Provide[
        "infra_container.logging_strategy"
    ],
    tracing_strategy: ITracingStrategy = Provide[
        "infra_container.tracing_strategy"
    ],
    metrics_strategy: IMetricsStrategy = Provide[
        "infra_container.metrics_strategy"
    ],
) -> _MonitorStrategies:
    """Resolve observability strategies via DI (used inside wrapper)."""
    return _MonitorStrategies(
        logging=logging_strategy,
        tracing=tracing_strategy,
        metrics=metrics_strategy,
    )


class _MonitoringHandler:
    """Handle logging/tracing/metrics for `monitor`.

    Delegates to injected strategies (passed in at construction).
    """

    def __init__(
        self,
        event_name: Events | str,
        *,
        strategies: _MonitorStrategies,
        options: _MonitorOptions,
    ) -> None:
        if isinstance(event_name, Events):
            self.event_name = event_name.value.code
        else:
            self.event_name = event_name
        self.logging_strategy = strategies.logging
        self.tracing_strategy = strategies.tracing
        self.metrics_strategy = strategies.metrics
        self.reraise = options.reraise
        self.action_when_exception = options.action_when_exception
        self.use_log_args = options.use_log_args
        self.use_log_result = options.use_log_result

    def log_start(
        self,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        named_args: dict[str, Any] | None = None,
    ) -> tuple[float, Any]:
        """Logs start and returns (start_time, log_context)."""
        context = self.logging_strategy.log_start(
            self.event_name,
            args,
            kwargs,
            use_log_args=self.use_log_args,
            named_args=named_args,
        )
        return perf_counter(), context

    def log_success(
        self,
        result: Any,
        start_time: float,
        context: Any,
    ) -> None:
        duration = perf_counter() - start_time
        self.metrics_strategy.record_request(
            event_name=self.event_name,
            duration=duration,
            status="success",
        )
        self.metrics_strategy.record_sla(
            event_name=self.event_name,
            duration=duration,
            success=True,
        )

        self.logging_strategy.log_success(
            self.event_name,
            result,
            context,
            use_log_result=self.use_log_result,
        )

    def log_error(
        self,
        exc: Exception,
        start_time: float,
        context: Any,
    ) -> None:
        duration = perf_counter() - start_time
        error_type = _classify_error(exc)
        self.metrics_strategy.record_request(
            event_name=self.event_name,
            duration=duration,
            status="error",
            error_type=error_type,
        )
        self.metrics_strategy.record_sla(
            event_name=self.event_name,
            duration=duration,
            success=False,
        )

        self.logging_strategy.log_error(self.event_name, exc, context)

        if self.action_when_exception:
            self._safe_execute_callback(exc)

    def _safe_execute_callback(self, exc: Exception) -> None:
        try:
            if self.action_when_exception:
                self.action_when_exception(exc)
        except Exception:
            logger.exception("monitor action_when_exception failed")


def _get_bound_arguments(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    """Resolve param names and values (including defaults) via inspect.

    Returns a dict param_name -> value, excluding 'self'. On bind/signature
    errors returns empty dict so callers can fall back to args/kwargs.
    """
    try:
        sig = inspect.signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        return {k: v for k, v in bound.arguments.items() if k != "self"}
    except (ValueError, TypeError):
        return {}


def _classify_error(exc: Exception) -> str:
    if isinstance(exc, BusinessError):
        return "business"
    if isinstance(exc, InfrastructureError):
        return "infrastructure"
    return "unknown"


def _async_wrapper[**P, R](
    func: Callable[P, Coroutine[Any, Any, R]],
    event_name: str,
    options: _MonitorOptions,
) -> Callable[P, Coroutine[Any, Any, R]]:
    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        strategies = _resolve_monitor_strategies()
        handler = _MonitoringHandler(
            event_name=event_name,
            strategies=strategies,
            options=options,
        )
        span = handler.tracing_strategy.start_span(handler.event_name)
        with span:
            named = (
                _get_bound_arguments(func, args, kwargs)
                if options.use_log_args
                else None
            )
            start_time, context = handler.log_start(args, kwargs, named)
            try:
                result = await func(*args, **kwargs)
            except Exception as exc:
                handler.log_error(exc, start_time, context)
                if handler.reraise:
                    raise
                return cast("R", None)

            handler.log_success(result, start_time, context)
            return result

    return cast("Callable[P, Coroutine[Any, Any, R]]", wrapper)


def _sync_wrapper[**P, R](
    func: Callable[P, R],
    event_name: str,
    options: _MonitorOptions,
) -> Callable[P, R]:
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        strategies = _resolve_monitor_strategies()
        handler = _MonitoringHandler(
            event_name=event_name,
            strategies=strategies,
            options=options,
        )
        span = handler.tracing_strategy.start_span(handler.event_name)
        with span:
            named = (
                _get_bound_arguments(func, args, kwargs)
                if options.use_log_args
                else None
            )
            start_time, context = handler.log_start(args, kwargs, named)
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                handler.log_error(exc, start_time, context)
                if handler.reraise:
                    raise
                return cast("R", None)

            handler.log_success(result, start_time, context)
            return result

    return cast("Callable[P, R]", wrapper)


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
        event_name_str = (
            event_name.value.code
            if isinstance(event_name, Events)
            else event_name
        )
        opts = _MonitorOptions(
            reraise=reraise,
            action_when_exception=action_when_exception,
            use_log_args=use_log_args,
            use_log_result=use_log_result,
        )
        if inspect.iscoroutinefunction(func):
            return cast(
                "Callable[P, Coroutine[Any, Any, R]]",
                _async_wrapper(
                    cast("Callable[P, Coroutine[Any, Any, R]]", func),
                    event_name_str,
                    opts,
                ),
            )
        return cast(
            "Callable[P, R]",
            _sync_wrapper(
                cast("Callable[P, R]", func),
                event_name_str,
                opts,
            ),
        )

    return cast(
        (
            "Callable[[Callable[P, R] | Callable[P, Coroutine[Any, Any, R]]], "
            "Any]"
        ),
        decorator,
    )
