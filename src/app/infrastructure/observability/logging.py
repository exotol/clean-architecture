from __future__ import annotations

import logging
import logging.config
from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter,
)
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from pythonjsonlogger import jsonlogger

from app.core.constants import OTLP_LOCAL_ENDPOINT

if TYPE_CHECKING:
    from app.utils.configs import LoggerConfig
    from app.utils.configs import OTLPConfig


def setup_logging(
    logger_config: LoggerConfig,
    otlp_config: OTLPConfig,
) -> None:
    # 0. Configure OpenTelemetry
    if not isinstance(trace.get_tracer_provider(), TracerProvider):
        resource = Resource.create(
            attributes={"service.name": otlp_config.service_name}
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
                    )
                )
            provider.add_span_processor(processor)
    
        trace.set_tracer_provider(provider)

    # Instrument logging to inject otelTraceID and otelSpanID
    LoggingInstrumentor().instrument(set_logging_formatter=False)

    # 1. Configure Standard Logging
    handlers = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stdout",
            "level": logger_config.level.value,
        }
    }
    
    if logger_config.path:
        handlers["file"] = {
            "class": "logging.FileHandler",
            "formatter": "json",
            "filename": logger_config.path,
            "mode": "a",
            "level": logger_config.level.value,
        }

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": jsonlogger.JsonFormatter,
                "format": "%(asctime)s %(levelname)s %(name)s %(message)s %(otelTraceID)s %(otelSpanID)s",
                "rename_fields": {
                    "asctime": "timestamp",
                    "levelname": "level",
                    "name": "logger",
                    "otelTraceID": "trace_id",
                    "otelSpanID": "span_id",
                },
            },
        },
        "handlers": handlers,
        "root": {
            "level": logger_config.level.value,
            "handlers": list(handlers.keys()),
        },
        "loggers": {
            # Configure third-party loggers if needed
        }
    }

    # Set external loggers to use our handlers and level
    for logger_name in logger_config.loggers_to_root:
        logging_config["loggers"][logger_name] = {
            "handlers": list(handlers.keys()),
            "level": logger_config.level.value,
            "propagate": False,
        }

    logging.config.dictConfig(logging_config)
