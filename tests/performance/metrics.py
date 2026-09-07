from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

import gevent
from gevent.pywsgi import WSGIServer
from locust import events
from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from prometheus_client import make_wsgi_app

from tests.performance.config import config


if TYPE_CHECKING:
    from opentelemetry.metrics import Counter
    from opentelemetry.metrics import Histogram


class _LocustMetricsListener:
    """Listener recording Locust request metrics into instruments."""

    def __init__(
        self,
        requests_counter: Counter,
        failures_counter: Counter,
        duration_histogram: Histogram,
    ) -> None:
        self._requests_counter = requests_counter
        self._failures_counter = failures_counter
        self._duration_histogram = duration_histogram

    def __call__(
        self,
        request_type: str,
        name: str,
        response_time: float,
        response_length: int,
        exception: Exception | None,
        **kwargs: Any,
    ) -> None:
        """Record metrics on every request."""
        _ = (response_length, kwargs)
        attributes = {"method": request_type, "name": name}

        if exception:
            self._failures_counter.add(
                1,
                attributes | {"error": str(exception)},
            )
        else:
            self._requests_counter.add(1, attributes | {"status": "success"})

        # response_time is in milliseconds, convert to seconds
        self._duration_histogram.record(response_time / 1000.0, attributes)


def setup_locust_metrics() -> None:
    """Configure OpenTelemetry metrics for Locust."""
    resource = Resource.create({"service.name": config.METRICS_SERVICE_NAME})
    reader = PrometheusMetricReader()
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)
    meter = metrics.get_meter(config.METRICS_SERVICE_NAME)

    # Define Instruments
    requests_counter = meter.create_counter(
        "locust_requests_total",
        description="Total number of requests",
    )
    failures_counter = meter.create_counter(
        "locust_failures_total",
        description="Total number of failures",
    )
    duration_histogram = meter.create_histogram(
        "locust_request_duration_seconds",
        description="Request duration in seconds",
    )

    listener = _LocustMetricsListener(
        requests_counter=requests_counter,
        failures_counter=failures_counter,
        duration_histogram=duration_histogram,
    )
    events.request.add_listener(listener)


def start_metrics_server() -> None:
    """
    Start Prometheus WSGI server in a gevent greenlet.
    """
    try:
        app = make_wsgi_app()
        http_server = WSGIServer(("", config.METRICS_PORT), app)
        gevent.spawn(http_server.serve_forever)
    except OSError:
        # Port might be in use if running multiple workers on the same machine
        pass
