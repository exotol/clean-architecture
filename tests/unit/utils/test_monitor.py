from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from app.core.events import Events
from app.core.exceptions import BusinessError
from app.core.exceptions import InfrastructureError
from app.utils.monitor import monitor


# --- Fixtures for strategies ---
@pytest.fixture
def mock_logging_strategy():
    return MagicMock()


@pytest.fixture
def mock_tracing_strategy():
    mock_span = MagicMock()
    mock_tracing = MagicMock()
    mock_tracing.start_span.return_value = mock_span
    mock_span.__enter__.return_value = mock_span
    mock_span.__exit__.return_value = None
    return mock_tracing


@pytest.fixture
def mock_metrics_strategy():
    return MagicMock()


@pytest.fixture(autouse=True)
def mock_dependencies(
    mock_logging_strategy,
    mock_tracing_strategy,
    mock_metrics_strategy,
):
    with (
        patch(
            "app.utils.monitor._get_logging_strategy",
            return_value=mock_logging_strategy,
        ),
        patch(
            "app.utils.monitor._get_tracing_strategy",
            return_value=mock_tracing_strategy,
        ),
        patch(
            "app.utils.monitor._get_metrics_strategy",
            return_value=mock_metrics_strategy,
        ),
    ):
        yield


# --- Sync Tests ---
def test_monitor_sync_success(
    mock_logging_strategy,
    mock_metrics_strategy,
    mock_tracing_strategy,
) -> None:
    # Arrange
    @monitor(event_name="test_sync")
    def sync_func(a, b):
        return a + b

    # Act
    result = sync_func(1, 2)

    # Assert
    assert result == 3
    # Check strategies
    mock_tracing_strategy.start_span.assert_called_once_with("test_sync")
    mock_logging_strategy.log_start.assert_called_once()
    mock_logging_strategy.log_success.assert_called_once()
    mock_metrics_strategy.record_request.assert_called_once()

    _args, kwargs = mock_metrics_strategy.record_request.call_args
    assert kwargs["status"] == "success"
    assert kwargs["event_name"] == "test_sync"


def test_monitor_sync_error(
    mock_logging_strategy,
    mock_metrics_strategy,
) -> None:
    # Arrange
    @monitor(event_name=Events.SEARCH_SERVICE, reraise=True)
    def sync_fail():
        err = BusinessError("Fail message")
        err.title = "fail"
        err.code = "FAIL"
        raise err

    # Act
    with pytest.raises(BusinessError):
        sync_fail()

    # Assert
    mock_logging_strategy.log_error.assert_called_once()
    mock_metrics_strategy.record_request.assert_called_once()

    _args, kwargs = mock_metrics_strategy.record_request.call_args
    assert kwargs["status"] == "error"
    assert kwargs["error_type"] == "business"


def test_monitor_sync_error_infrastructure(
    mock_metrics_strategy,
) -> None:
    # Arrange
    @monitor(event_name="infra_test")
    def sync_fail():
        raise InfrastructureError("db fail")

    # Act
    with pytest.raises(InfrastructureError):
        sync_fail()

    # Assert
    _args, kwargs = mock_metrics_strategy.record_request.call_args
    assert kwargs["error_type"] == "infrastructure"


def test_monitor_sync_suppress_exception(
) -> None:
    # Arrange
    @monitor(event_name="suppress", reraise=False)
    def sync_fail():
        raise ValueError("boom")

    # Act
    result = sync_fail()

    # Assert
    assert result is None


def test_monitor_callback_error(mock_logging_strategy: MagicMock) -> None:
    # Test that exception in callback is suppressed
    callback = MagicMock(side_effect=ValueError("Callback failed"))

    @monitor(
        Events.SEARCH_SERVICE, action_when_exception=callback, reraise=False,
    )
    def func():
        raise RuntimeError("Original error")

    # Should not raise
    func()

    callback.assert_called_once()  # Should return None if suppressed
    mock_logging_strategy.log_error.assert_called_once()


# --- Async Tests ---
@pytest.mark.asyncio
async def test_monitor_async_success(
    mock_metrics_strategy,
) -> None:
    # Arrange
    @monitor(event_name="async_test")
    async def async_func(x):
        return x * 2

    # Act
    result = await async_func(5)

    # Assert
    assert result == 10
    mock_metrics_strategy.record_request.assert_called_once()
    assert (
        mock_metrics_strategy.record_request.call_args[1]["status"]
        == "success"
    )


@pytest.mark.asyncio
async def test_monitor_async_error(
    mock_metrics_strategy,
) -> None:
    # Arrange
    @monitor(event_name="async_error")
    async def async_fail():
        raise ValueError("async boom")

    # Act
    with pytest.raises(ValueError, match="async boom"):
        await async_fail()

    # Assert
    mock_metrics_strategy.record_request.assert_called_once()
    assert (
        mock_metrics_strategy.record_request.call_args[1]["status"] == "error"
    )
