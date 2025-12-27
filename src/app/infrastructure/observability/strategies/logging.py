from __future__ import annotations

from typing import Any
from typing import TYPE_CHECKING

from loguru import logger as loguru_logger

from app.domain.interfaces.observability import ILoggingStrategy

if TYPE_CHECKING:
    from app.utils.serializer import ItemSerializer


class StandardLoggingStrategy(ILoggingStrategy):
    """
    Logging strategy using Loguru.
    Stateless - all configuration passed via method arguments.
    Uses ItemSerializer for fast, non-recursive serialization.
    """

    def __init__(self, serializer: ItemSerializer) -> None:
        self._serializer = serializer

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

        loguru_logger.bind(**context).info("{}_SEND", event_name)
        return loguru_logger.bind(**context)

    def log_success(
        self,
        event_name: str,
        result: Any,
        context: Any,
        *,
        use_log_result: bool,
    ) -> None:
        bound_logger = context
        if use_log_result:
            bound_logger = bound_logger.bind(result=self._serializer.serialize(result))
        bound_logger.info("{}_SUCCESS", event_name)

    def log_error(self, event_name: str, exc: Exception, context: Any) -> None:
        bound_logger = context
        bound_logger.exception("{}_ERROR", event_name)
