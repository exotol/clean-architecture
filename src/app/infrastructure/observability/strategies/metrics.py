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

    def record_request(
        self,
        event_name: str,
        duration: float,
        status: str,
        error_type: str | None = None,
    ) -> None:
        attributes = {"event": event_name, "status": status}
        if error_type:
            attributes["error_type"] = error_type

        self.requests_total.add(1, attributes)
        self.request_duration.record(duration, {"event": event_name})
