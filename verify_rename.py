"""Small local script to verify JSON log field renaming."""

from __future__ import annotations

import logging
import sys
from typing import Any

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from pythonjsonlogger import jsonlogger


# Setup OTel (dummy)
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom formatter placeholder used by the script."""

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        """Add extra fields to the JSON log record."""
        super().add_fields(log_record, record, message_dict)


# Manually simulate what LoggingInstrumentor does (injects attributes)
# Or just use the config style we have
logger = logging.getLogger("test_rename")
handler = logging.StreamHandler(sys.stdout)
formatter = jsonlogger.JsonFormatter(
    "%(message)s %(otelTraceID)s %(otelSpanID)s",
    rename_fields={
        "otelTraceID": "trace_id",
        "otelSpanID": "span_id",
    },
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Simulate injection
extra = {
    "otelTraceID": "00000000000000000000000000000123",
    "otelSpanID": "0000000000000456",
}
logger.info("Test message", extra=extra)
