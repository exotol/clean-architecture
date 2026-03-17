from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any
from typing import override

import structlog

from app.domain.interfaces.observability import ILoggingStrategy


if TYPE_CHECKING:
    from app.utils.serializer import ItemSerializer


def _logger() -> structlog.stdlib.BoundLogger:
    """Return structlog logger for this module (stdlib-backed, same JSON)."""
    return structlog.stdlib.get_logger(__name__)


class StandardLoggingStrategy(ILoggingStrategy):
    """Logging strategy using structlog on top of stdlib logging.

    Stateless: all configuration passed via method arguments.
    Uses `ItemSerializer` for safe, non-recursive serialization.
    """

    def __init__(self, serializer: ItemSerializer) -> None:
        self._serializer = serializer

    @override
    def log_start(
        self,
        event_name: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        *,
        use_log_args: bool,
        named_args: dict[str, Any] | None = None,
    ) -> Any:
        context: dict[str, Any] = {"event": event_name}
        if use_log_args:
            if named_args:
                for k, v in named_args.items():
                    context[k] = self._serializer.serialize(v)
            else:
                context["args"] = self._serializer.serialize(args)
                context["kwargs"] = self._serializer.serialize(kwargs)

        # Omit "event" to avoid duplicate with structlog event arg
        log_kw = {k: v for k, v in context.items() if k != "event"}
        _logger().info(f"{event_name}_SEND", **log_kw)
        return context

    @override
    def log_success(
        self,
        event_name: str,
        result: Any,
        context: Any,
        *,
        use_log_result: bool,
    ) -> None:
        log_context = dict(context) if isinstance(context, dict) else {}

        if use_log_result:
            log_context["result"] = self._serializer.serialize(result)
        log_kw = {k: v for k, v in log_context.items() if k != "event"}
        _logger().info(f"{event_name}_SUCCESS", **log_kw)

    @override
    def log_error(self, event_name: str, exc: Exception, context: Any) -> None:
        log_context = context if isinstance(context, dict) else {}
        log_kw = {k: v for k, v in log_context.items() if k != "event"}
        _logger().error(
            f"{event_name}_ERROR",
            exc_info=exc,
            **log_kw,
        )
