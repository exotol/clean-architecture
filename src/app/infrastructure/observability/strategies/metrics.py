from __future__ import annotations

from opentelemetry import metrics

from app.core import constants
from app.domain.interfaces.observability import IMetricsStrategy


class OpentelemetryMetricsStrategy(IMetricsStrategy):
    """Metrics strategy using OpenTelemetry."""

    def __init__(self) -> None:
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
        self.sla_requests_total = self.meter.create_counter(
            name=constants.METRICS_SLA_REQUESTS_TOTAL_NAME,
            description=constants.METRICS_SLA_REQUESTS_TOTAL_DESC,
            unit=constants.METRICS_SLA_REQUESTS_TOTAL_UNIT,
        )
        self.sla_latency = self.meter.create_histogram(
            name=constants.METRICS_SLA_LATENCY_NAME,
            description=constants.METRICS_SLA_LATENCY_DESC,
            unit=constants.METRICS_SLA_LATENCY_UNIT,
        )

    def record_request(
        self,
        event_name: str,
        duration: float,
        status: str,
        error_type: str | None = None,
    ) -> None:
        """Record request metrics."""
        attributes = {"event": event_name, "status": status}
        if error_type:
            attributes["error_type"] = error_type

        self.requests_total.add(1, attributes)
        self.request_duration.record(duration, {"event": event_name})

    def record_sla(
        self,
        event_name: str,
        duration: float,
        *,
        success: bool,
    ) -> None:
        """Record SLA metrics (latency + success/error for error rate)."""
        status = "success" if success else "error"
        self.sla_requests_total.add(1, {"event": event_name, "status": status})
        self.sla_latency.record(duration, {"event": event_name})
