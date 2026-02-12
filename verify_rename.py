
import logging
import sys
from pythonjsonlogger import jsonlogger
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

# Setup OTel (dummy)
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Setup Logging
class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        # Verify renaming happened or force it if needed
        pass

# Manually simulate what LoggingInstrumentor does (injects attributes)
# Or just use the config style we have
logger = logging.getLogger("test_rename")
handler = logging.StreamHandler(sys.stdout)
formatter = jsonlogger.JsonFormatter(
    "%(message)s %(otelTraceID)s %(otelSpanID)s",
    rename_fields={
        "otelTraceID": "trace_id",
        "otelSpanID": "span_id"
    }
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Simulate injection
extra = {"otelTraceID": "00000000000000000000000000000123", "otelSpanID": "0000000000000456"}
logger.info("Test message", extra=extra)
