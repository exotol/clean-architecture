"""Unit tests for common endpoint handlers (healthcheck, root, metrics)."""

from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

from app.presentation.api.common.endpoints.healthcheck import healthcheck
from app.presentation.api.common.endpoints.metrics import get_metrics
from app.presentation.api.common.endpoints.root import root
from app.presentation.api.schemas.healthcheck import Healthcheck


def test_healthcheck_returns_healthcheck_schema() -> None:
    """healthcheck() returns Healthcheck instance."""
    mock_strategies = MagicMock()
    mock_strategies.logging.log_start.return_value = {}
    mock_strategies.tracing.start_span.return_value.__enter__ = MagicMock(
        return_value=MagicMock(),
    )
    mock_strategies.tracing.start_span.return_value.__exit__ = MagicMock(
        return_value=None,
    )
    with patch(
        "app.utils.monitor._resolve_monitor_strategies",
        return_value=mock_strategies,
    ):
        result = healthcheck()
    assert isinstance(result, Healthcheck)


def test_root_returns_hello_world() -> None:
    """root() returns HelloWorld with message."""
    result = root()
    assert "Hello" in result.message


def test_get_metrics_returns_response() -> None:
    """get_metrics() returns Response with Prometheus content."""
    result = get_metrics()
    assert result.media_type == "text/plain"
    assert len(result.body) > 0
