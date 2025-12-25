from fastapi import APIRouter
from fastapi import Response
from opentelemetry import metrics
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from prometheus_client import generate_latest

router = APIRouter()


@router.get("/metrics")
def get_metrics() -> Response:
    """
    Expose Prometheus metrics.
    """
    # Force collection of metrics
    provider = metrics.get_meter_provider()
    if isinstance(provider, MeterProvider):
        for reader in provider._sdk_config.metric_readers:
            if isinstance(reader, PrometheusMetricReader):
                reader.collect()

    return Response(
        content=generate_latest(),
        media_type="text/plain",
    )
