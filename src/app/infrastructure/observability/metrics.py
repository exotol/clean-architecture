from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource


def setup_metrics() -> None:
    """
    Configure OpenTelemetry metrics with Prometheus exporter.
    """
    # Create a reader to export metrics to Prometheus
    reader = PrometheusMetricReader()

    # Create a MeterProvider with the reader
    provider = MeterProvider(
        resource=Resource.create({"service.name": "eva"}),
        metric_readers=[reader],
    )

    # Set the global MeterProvider
    metrics.set_meter_provider(provider)
