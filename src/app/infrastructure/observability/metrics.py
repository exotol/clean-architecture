from dependency_injector.wiring import inject, Provide
from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.view import ExplicitBucketHistogramAggregation
from opentelemetry.sdk.metrics.view import View
from opentelemetry.sdk.resources import Resource

from app.core.constants import METRICS_REQUEST_DURATION_NAME
from app.core.containers import AppContainer
from app.utils.configs import MetricsConfig


@inject
def setup_metrics(
    metrics_config: MetricsConfig = Provide[
        AppContainer.infra_container.metrics_config
    ],
) -> None:
    """
    Configure OpenTelemetry metrics with Prometheus exporter.
    """
    # Create a reader to export metrics to Prometheus
    reader = PrometheusMetricReader()

    duration_buckets = metrics_config.duration_buckets

    view = View(
        instrument_name=METRICS_REQUEST_DURATION_NAME,
        aggregation=ExplicitBucketHistogramAggregation(
            boundaries=duration_buckets
        ),
    )

    # Create a MeterProvider with the reader and view
    provider = MeterProvider(
        resource=Resource.create(
            {
                "service.name": metrics_config.service_name
            }
        ),
        metric_readers=[reader],
        views=[view],
    )

    # Set the global MeterProvider
    metrics.set_meter_provider(provider)
