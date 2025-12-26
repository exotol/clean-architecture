from typing import Any

from opentelemetry import trace

from app.domain.interfaces.observability import ITracingStrategy


class OpentelemetryTracingStrategy(ITracingStrategy):
    """Tracing strategy using OpenTelemetry."""

    def __init__(self) -> None:
        self.tracer = trace.get_tracer(__name__)

    def start_span(self, name: str) -> Any:
        return self.tracer.start_as_current_span(name, kind=trace.SpanKind.INTERNAL)

    def end_span(self, span: Any, exc: Exception | None = None) -> None:
        # Context manager handles ending, but if we needed manual control:
        # span.end()
        pass
