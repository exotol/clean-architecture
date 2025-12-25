import gevent
from gevent.pywsgi import WSGIServer
from locust import events
from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from prometheus_client import make_wsgi_app

from tests.performance.config import config


def setup_locust_metrics() -> None:
    """
    Configure OpenTelemetry metrics for Locust.
    """
    resource = Resource.create({"service.name": config.METRICS_SERVICE_NAME})
    reader = PrometheusMetricReader()
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)
    meter = metrics.get_meter(config.METRICS_SERVICE_NAME)

    # Define Instruments
    requests_counter = meter.create_counter(
        "locust_requests_total", description="Total number of requests"
    )
    failures_counter = meter.create_counter(
        "locust_failures_total", description="Total number of failures"
    )
    duration_histogram = meter.create_histogram(
        "locust_request_duration_seconds",
        description="Request duration in seconds",
    )

    @events.request.add_listener
    def on_request(
        request_type: str,
        name: str,
        response_time: float,
        response_length: int,
        exception: Exception | None,
        **kwargs,
    ) -> None:
        """
        Record metrics on every request.
        """
        attributes = {"method": request_type, "name": name}

        if exception:
            failures_counter.add(1, attributes | {"error": str(exception)})
        else:
            requests_counter.add(1, attributes | {"status": "success"})

        # response_time is in milliseconds, convert to seconds
        duration_histogram.record(response_time / 1000.0, attributes)


def start_metrics_server() -> None:
    """
    Start Prometheus WSGI server in a gevent greenlet.
    """
    try:
        print(
            f"Starting Prometheus WSGI server on port {config.METRICS_PORT}"
        )
        app = make_wsgi_app()
        http_server = WSGIServer(("", config.METRICS_PORT), app)
        gevent.spawn(http_server.serve_forever)
    except OSError:
        # Port might be in use if running multiple workers on the same machine
        pass
