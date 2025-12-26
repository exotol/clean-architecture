import dataclasses
import json
from typing import Any

from loguru import logger as loguru_logger
from pydantic import BaseModel

from app.domain.interfaces.observability import ILoggingStrategy


class StandardLoggingStrategy(ILoggingStrategy):
    """
    Logging strategy using Loguru.
    Stateless - all configuration passed via method arguments.
    """

    def log_start(
        self,
        event_name: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        *,
        use_log_args: bool = True,
    ) -> Any:
        context: dict[str, Any] = {"event": event_name}
        if use_log_args:
            context["args"] = self._serialize_payload(args)
            context["kwargs"] = self._serialize_payload(kwargs)

        loguru_logger.bind(**context).info("{}_SEND", event_name)
        return loguru_logger.bind(**context)

    def log_success(
        self,
        event_name: str,
        result: Any,
        context: Any,
        *,
        use_log_result: bool = True,
    ) -> None:
        bound_logger = context
        if use_log_result:
            bound_logger = bound_logger.bind(result=self._serialize_payload(result))
        bound_logger.info("{}_SUCCESS", event_name)

    def log_error(self, event_name: str, exc: Exception, context: Any) -> None:
        bound_logger = context
        bound_logger.exception("{}_ERROR", event_name)

    def _serialize_payload(self, obj: Any) -> Any:
        if isinstance(obj, BaseModel):
            return obj.model_dump(mode="json")
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return dataclasses.asdict(obj)
        if isinstance(obj, list | tuple | set):
            return [self._serialize_payload(item) for item in obj]
        if isinstance(obj, dict):
            return {str(key): self._serialize_payload(val) for key, val in obj.items()}
        return self._serialize_fallback(obj)

    def _serialize_fallback(self, obj: Any) -> Any:
        if isinstance(obj, str | int | float | bool | type(None)):
            return obj
        try:
            return json.dumps(obj)
        except (TypeError, ValueError):
            return str(obj)
