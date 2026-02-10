from unittest.mock import patch, MagicMock
from app.infrastructure.observability.metrics import setup_metrics
from app.utils.configs import MetricsConfig

def test_setup_metrics() -> None:
    config = MetricsConfig(duration_buckets=[0.1, 0.2], service_name="test")
    
    with patch("app.infrastructure.observability.metrics.metrics") as mock_metrics, \
         patch("app.infrastructure.observability.metrics.MeterProvider") as MockProvider, \
         patch("app.infrastructure.observability.metrics.PrometheusMetricReader") as MockReader, \
         patch("app.infrastructure.observability.metrics.View") as MockView, \
         patch("app.infrastructure.observability.metrics.Resource") as MockResource:
         
        setup_metrics.__wrapped__(config)
        
        MockReader.assert_called_once()
        MockView.assert_called_once()
        MockProvider.assert_called_once()
        mock_metrics.set_meter_provider.assert_called_once()
