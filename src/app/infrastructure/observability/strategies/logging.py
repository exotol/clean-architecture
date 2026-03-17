from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from typing import Any
from typing import override

from app.domain.interfaces.observability import ILoggingStrategy


if TYPE_CHECKING:
    from app.utils.serializer import ItemSerializer

logger = logging.getLogger(__name__)


class StandardLoggingStrategy(ILoggingStrategy):
    """Logging strategy using standard Python logging.

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
    ) -> Any:
        context: dict[str, Any] = {"event": event_name}
        if use_log_args:
            context["args"] = self._serializer.serialize(args)
            context["kwargs"] = self._serializer.serialize(kwargs)

        # Use extra to pass context to JSONFormatter
        logger.info("%s_SEND", event_name, extra=context)
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
        # context is the dict we returned in log_start
        log_context = context if isinstance(context, dict) else {}

        if use_log_result:
            log_context["result"] = self._serializer.serialize(result)

        logger.info("%s_SUCCESS", event_name, extra=log_context)

    @override
    def log_error(self, event_name: str, exc: Exception, context: Any) -> None:
        log_context = context if isinstance(context, dict) else {}
        logger.error("%s_ERROR", event_name, exc_info=exc, extra=log_context)
