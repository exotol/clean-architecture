from __future__ import annotations

from unittest.mock import patch

from app.infrastructure.observability.metrics import setup_metrics
from app.utils.configs import MetricsConfig


def test_setup_metrics() -> None:
    config = MetricsConfig(duration_buckets=[0.1, 0.2], service_name="test")

    with (
        patch(
            "app.infrastructure.observability.metrics.metrics",
        ) as mock_metrics,
        patch(
            "app.infrastructure.observability.metrics.MeterProvider",
        ) as mock_provider,
        patch(
            "app.infrastructure.observability.metrics.PrometheusMetricReader",
        ) as mock_reader,
        patch("app.infrastructure.observability.metrics.View") as mock_view,
        patch("app.infrastructure.observability.metrics.Resource"),
    ):
        setup_metrics.__wrapped__(config)

        mock_reader.assert_called_once()
        mock_view.assert_called_once()
        mock_provider.assert_called_once()
        mock_metrics.set_meter_provider.assert_called_once()
