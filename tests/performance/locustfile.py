import gevent
from gevent.pywsgi import WSGIServer
from locust import HttpUser
from locust import between
from locust import constant
from locust import events
from locust import task
from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from prometheus_client import make_wsgi_app

# Setup OpenTelemetry
resource = Resource.create({"service.name": "locust"})
reader = PrometheusMetricReader()
provider = MeterProvider(resource=resource, metric_readers=[reader])
metrics.set_meter_provider(provider)
meter = metrics.get_meter("locust")

# Define Instruments
requests_counter = meter.create_counter(
    "locust_requests_total", description="Total number of requests"
)
failures_counter = meter.create_counter(
    "locust_failures_total", description="Total number of failures"
)
duration_histogram = meter.create_histogram(
    "locust_request_duration_seconds", description="Request duration in seconds"
)


# Start Prometheus HTTP server
# Start on port 23456 to avoid conflict
try:
    app = make_wsgi_app()
    http_server = WSGIServer(("", 8888), app)
    gevent.spawn(http_server.serve_forever)
except OSError:
    # Port might be in use if running multiple workers on the same machine
    pass


@events.request.add_listener
def on_request(
    request_type, name, response_time, response_length, exception, **kwargs
):
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


class EvaUser(HttpUser):
    """
    Simulates a user interacting with the EVA service.
    """

    wait_time = between(1, 5)  # Wait between 1 and 5 seconds between tasks
    host = "http://localhost:8000"  # Default host for Web UI

    @task(3)
    def healthcheck(self) -> None:
        """
        Check the health of the service.
        Higher weight (3) means this task is executed more often.
        """
        self.client.get("/common/healthcheck", name="Healthcheck")

    @task(1)
    def root(self) -> None:
        """
        Visit the root endpoint.
        """
        self.client.get("/common/", name="Root")

    @task(2)
    def search(self) -> None:
        """
        Perform a search query.
        """
        # In a real scenario, you might want to randomize the query
        self.client.post(
            "/v1/answer/generate",
            json={"query": "test"},
            name="Search",
        )


class EvaStressUser(EvaUser):
    """
    Stress test user with no wait time to maximize RPS.
    """

    wait_time = constant(0)
