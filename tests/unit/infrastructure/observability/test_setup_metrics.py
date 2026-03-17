from __future__ import annotations

from unittest.mock import patch

from app.infrastructure.observability.metrics import setup_metrics
from app.utils.configs import MetricsConfig


def test_setup_metrics() -> None:
    # Arrange
    config = MetricsConfig(
        duration_buckets=[0.1, 0.2],
        service_name="test",
    )

    # Act
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
        setup_metrics(metrics_config=config)

        # Assert
        assert mock_reader.call_count == 1, (
            f"Expected PrometheusMetricReader() called once, "
            f"got {mock_reader.call_count}"
        )
        assert mock_view.call_count == 1, (
            f"Expected View() called once, got {mock_view.call_count}"
        )
        assert mock_provider.call_count == 1, (
            f"Expected MeterProvider() called once, "
            f"got {mock_provider.call_count}"
        )
        mock_metrics.set_meter_provider.assert_called_once()
