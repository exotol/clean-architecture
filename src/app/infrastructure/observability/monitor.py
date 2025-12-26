from __future__ import annotations

import dataclasses
import functools
import inspect
import json
from time import perf_counter
from typing import Any
from typing import ParamSpec
from typing import TYPE_CHECKING
from typing import TypeVar
from typing import cast

from loguru import logger
from opentelemetry import trace, metrics
from pydantic import BaseModel

from app.core import constants
from app.core.exceptions import BusinessError
from app.core.exceptions import InfrastructureError

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Coroutine

    from loguru import Logger

    from app.infrastructure.services.metrics_service import MetricsService

from app.infrastructure.observability.events import Events  # noqa: TC001


# --- Typing ---
P = ParamSpec("P")
R = TypeVar("R")

tracer = trace.get_tracer(__name__)


class _MonitoringHandler:
    """
    Helper class to handle logging and tracing logic for the monitor decorator.
    Separating this logic reduces the complexity of the decorator wrapper.
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
            self.event_description: str | None = event_name.value.description
        else:
            self.event_name = event_name
            self.event_description = None

        self.reraise = reraise
        self.action_when_exception = action_when_exception
        self.use_log_args = use_log_args
        self.use_log_result = use_log_result
        self._metrics_service: MetricsService | None = None

        # Copy metadata from wrapped function
        self.__name__ = getattr(func, "__name__", "wrapper")
        self.__doc__ = getattr(func, "__doc__", None)
        self.__wrapped__ = func

        # Metrics
        self.meter = metrics.get_meter(__name__)
        self.requests_total = self.meter.create_counter(
            name=constants.METRICS_REQUESTS_TOTAL_NAME,
            description=constants.METRICS_REQUESTS_TOTAL_DESC,
            unit=constants.METRICS_REQUESTS_TOTAL_UNIT,
        )
        self.request_duration = self.meter.create_histogram(
            name=constants.METRICS_REQUEST_DURATION_NAME,
            description=constants.METRICS_REQUEST_DURATION_DESC,
            unit=constants.METRICS_REQUEST_DURATION_UNIT,
        )

    def record_request(
        self,
        event_name: str,
        duration: float,
        status: str,
        error_type: str | None = None,
    ) -> None:
        """
        Record request metrics.

        Args:
            event_name: Name of the event/service.
            duration: Duration of the request in seconds.
            status: Status of the request (success/error).
            error_type: Type of error (business/infrastructure/unknown) if any.
        """
        attributes = {"event": event_name, "status": status}
        if error_type:
            attributes["error_type"] = error_type

        self.requests_total.add(1, attributes)
        self.request_duration.record(duration, {"event": event_name})

    def get_bound_logger(
        self, args: tuple[object, ...], kwargs: dict[str, object]
    ) -> Logger:
        """
        Creates a context-bound logger.

        Args:
            args: Positional arguments.
            kwargs: Keyword arguments.

        Returns:
            Logger with bound context.
        """
        context: dict[str, object] = {"event": self.event_name}
        if self.event_description:
            context["event_description"] = self.event_description

        if self.use_log_args:
            try:
                signature = inspect.signature(self.func)
                bound = signature.bind(*args, **kwargs)
                bound.apply_defaults()

                func_args = {}
                func_kwargs = {}

                for name, value in bound.arguments.items():
                    if name in {"self", "cls"}:
                        continue

                    param = signature.parameters[name]
                    if param.kind == inspect.Parameter.VAR_KEYWORD:
                        func_kwargs.update(value)
                    else:
                        func_args[name] = value

                context["args"] = _serialize_payload(func_args)
                context["kwargs"] = _serialize_payload(func_kwargs)
            except Exception:
                context["args_error"] = "Serialization failed"
                context["args"] = [_serialize_payload(arg) for arg in args]
                context["kwargs"] = {
                    key: _serialize_payload(val) for key, val in kwargs.items()
                }

        return logger.bind(**context)

    def log_start(self, bound_logger: Logger) -> float:
        """
        Logs the start of the event.

        Args:
            bound_logger: Logger instance.

        Returns:
            Start time of the event.
        """
        bound_logger.info("{}_SEND", self.event_name)
        return perf_counter()

    def log_success(
        self, bound_logger: Logger, result: object, start_time: float
    ) -> None:
        """
        Logs the success of the event.

        Args:
            bound_logger: Logger instance.
            result: Function result.
            start_time: Start time of the event.
        """
        duration = perf_counter() - start_time
        self.record_request(
            event_name=self.event_name,
            duration=duration,
            status="success",
        )

        if self.use_log_result:
            bound_logger = bound_logger.bind(result=_serialize_payload(result))
        bound_logger.info("{}_SUCCESS", self.event_name)

    def log_error(
        self, bound_logger: Logger, exc: Exception, start_time: float
    ) -> None:
        """
        Logs the error of the event.

        Args:
            bound_logger: Logger instance.
            exc: Exception raised.
            start_time: Start time of the event.
        """
        duration = perf_counter() - start_time
        error_type = _classify_error(exc)
        self.record_request(
            event_name=self.event_name,
            duration=duration,
            status="error",
            error_type=error_type,
        )

        if error_type == "business":
            bound_logger.warning(
                "{event_name}_WARNING: {exc}",
                event_name=self.event_name,
                exc=exc,
            )
        else:
            bound_logger.exception("{}_ERROR", self.event_name)

        if self.action_when_exception:
            self._safe_execute_callback(exc)

    def _safe_execute_callback(self, exc: Exception) -> None:
        try:
            if self.action_when_exception:
                self.action_when_exception(exc)
        except Exception as callback_exc:
            logger.error(
                f"Callback action_when_exception failed: {callback_exc}"
            )


def _classify_error(exc: Exception) -> str:
    if isinstance(exc, BusinessError):
        return "business"
    if isinstance(exc, InfrastructureError):
        return "infrastructure"
    return "unknown"


def _serialize_payload(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    if isinstance(obj, list | tuple | set):
        return [_serialize_payload(item) for item in obj]
    if isinstance(obj, dict):
        return {str(key): _serialize_payload(val) for key, val in obj.items()}

    return _serialize_fallback(obj)


def _serialize_fallback(obj: Any) -> Any:
    if isinstance(obj, str | int | float | bool | type(None)):
        return obj
    try:
        return json.dumps(obj)
    except (TypeError, ValueError):
        return str(obj)


def _async_wrapper(  # noqa: UP047
    func: Callable[P, Coroutine[Any, Any, R]],
    handler: _MonitoringHandler,
) -> Callable[P, Coroutine[Any, Any, R]]:
    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        with tracer.start_as_current_span(
            handler.event_name, kind=trace.SpanKind.INTERNAL
        ):
            bound_logger = handler.get_bound_logger(args, kwargs)
            start_time = handler.log_start(bound_logger)

            try:
                result = await func(*args, **kwargs)
            except Exception as exc:
                handler.log_error(bound_logger, exc, start_time)
                if handler.reraise:
                    raise
                return cast("R", None)

            handler.log_success(bound_logger, result, start_time)
            return result

    return wrapper


def _sync_wrapper(  # noqa: UP047
    func: Callable[P, R],
    handler: _MonitoringHandler,
) -> Callable[P, R]:
    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        with tracer.start_as_current_span(
            handler.event_name, kind=trace.SpanKind.INTERNAL
        ):
            bound_logger = handler.get_bound_logger(args, kwargs)
            start_time = handler.log_start(bound_logger)

            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                handler.log_error(bound_logger, exc, start_time)
                if handler.reraise:
                    raise
                return cast("R", None)

            handler.log_success(bound_logger, result, start_time)
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
    """
    Decorator factory for monitoring function execution.

    Args:
        event_name: Name of the event for logging and tracing.
        reraise: Whether to reraise exceptions.
        action_when_exception: Optional callback to execute on exception.
        use_log_args: Whether to log function arguments.
        use_log_result: Whether to log function result.

    Returns:
        Decorated function.
    """

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
