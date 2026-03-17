from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING
from typing import Any


if TYPE_CHECKING:
    from collections.abc import MutableMapping

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.export import ConsoleSpanExporter
import structlog

from app.core.constants import OTLP_LOCAL_ENDPOINT


if TYPE_CHECKING:
    from app.utils.configs import LoggerConfig
    from app.utils.configs import OTLPConfig


def _add_trace_span_from_record(
    _logger: Any,
    _method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Add trace_id and span_id from LogRecord to event_dict."""
    record = event_dict.get("_record")
    if record is not None:
        event_dict["trace_id"] = getattr(record, "otelTraceID", None)
        event_dict["span_id"] = getattr(record, "otelSpanID", None)
    return event_dict


def _build_shared_processors() -> list[Any]:
    """Processors shared by structlog and ProcessorFormatter."""
    return [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.format_exc_info,
    ]


def _build_structlog_formatter() -> structlog.stdlib.ProcessorFormatter:
    """Build ProcessorFormatter for unified JSON (structlog + stdlib)."""
    return structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=_build_shared_processors(),
        processors=[
            _add_trace_span_from_record,
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )


def _configure_otel(otlp_config: OTLPConfig) -> None:
    """Set up OpenTelemetry tracer provider and instrument logging."""
    if isinstance(trace.get_tracer_provider(), TracerProvider):
        return
    resource = Resource.create(
        attributes={"service.name": otlp_config.service_name},
    )
    provider = TracerProvider(resource=resource)
    if otlp_config.enabled:
        if otlp_config.endpoint == OTLP_LOCAL_ENDPOINT:
            processor = BatchSpanProcessor(ConsoleSpanExporter())
        else:
            processor = BatchSpanProcessor(
                OTLPSpanExporter(
                    endpoint=otlp_config.endpoint,
                    insecure=otlp_config.insecure,
                ),
            )
        provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    LoggingInstrumentor().instrument(set_logging_formatter=False)


def _configure_structlog() -> None:
    """Configure structlog to use stdlib and ProcessorFormatter."""
    wrap = structlog.stdlib.ProcessorFormatter.wrap_for_formatter
    structlog.configure(
        processors=[*_build_shared_processors(), wrap],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def _configure_stdlib_handlers(logger_config: LoggerConfig) -> None:
    """Attach ProcessorFormatter handlers to root and named loggers."""
    formatter = _build_structlog_formatter()
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logger_config.level.value)
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logger_config.level.value)
    root.addHandler(console_handler)

    file_handler: logging.FileHandler | None = None
    if logger_config.path:
        file_handler = logging.FileHandler(logger_config.path, mode="a")
        file_handler.setLevel(logger_config.level.value)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    for logger_name in logger_config.loggers_to_root:
        child = logging.getLogger(logger_name)
        child.setLevel(logger_config.level.value)
        child.propagate = False
        child.handlers.clear()
        child.addHandler(console_handler)
        if file_handler is not None:
            child.addHandler(file_handler)


def setup_logging(
    logger_config: LoggerConfig,
    otlp_config: OTLPConfig,
) -> None:
    """Configure structlog on top of stdlib logging for unified JSON output.

    Business code uses structlog.get_logger() for context and clean API;
    uvicorn, sqlalchemy, httpx (stdlib) logs are formatted the same via
    ProcessorFormatter.
    """
    _configure_otel(otlp_config)
    _configure_structlog()
    _configure_stdlib_handlers(logger_config)
