from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from app.core.events import Events
from app.core.exceptions import BusinessError
from app.core.exceptions import InfrastructureError
from app.utils.monitor import monitor


if TYPE_CHECKING:
    from app.core.containers import AppContainer


# --- Fixtures: strategies from DI container overrides (conftest) ---
@pytest.fixture(autouse=True)
def rewire_mock_container(di_container: AppContainer) -> None:
    """Re-wire app package to test container (undo create_app wiring)."""
    di_container.wire(packages=["app"])


@pytest.fixture(autouse=True)
def reset_strategy_mocks(di_container: AppContainer) -> None:
    """Reset strategy mocks before each test for isolated assertions."""
    di_container.infra_container.logging_strategy().reset_mock()
    di_container.infra_container.tracing_strategy().reset_mock()
    di_container.infra_container.metrics_strategy().reset_mock()


@pytest.fixture
def mock_tracing_strategy(di_container: AppContainer) -> MagicMock:
    """Configure container's tracing mock with span context manager."""
    mock_tracing = di_container.infra_container.tracing_strategy()
    mock_span = MagicMock()
    mock_tracing.start_span.return_value = mock_span
    mock_span.__enter__.return_value = mock_span
    mock_span.__exit__.return_value = None
    return mock_tracing


# --- Sync Tests ---
def test_monitor_sync_success(
    di_container: AppContainer,
    mock_tracing_strategy: MagicMock,
) -> None:
    # Arrange
    @monitor(event_name="test_sync")
    def sync_func(a, b):
        return a + b

    # Act
    result = sync_func(1, 2)

    # Assert
    assert result == 3
    logging_strategy = di_container.infra_container.logging_strategy()
    metrics_strategy = di_container.infra_container.metrics_strategy()
    mock_tracing_strategy.start_span.assert_called_once_with("test_sync")
    logging_strategy.log_start.assert_called_once()
    logging_strategy.log_success.assert_called_once()
    metrics_strategy.record_request.assert_called_once()

    _args, kwargs = metrics_strategy.record_request.call_args
    assert kwargs["status"] == "success"
    assert kwargs["event_name"] == "test_sync"


def test_monitor_sync_error(di_container: AppContainer) -> None:
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
    logging_strategy = di_container.infra_container.logging_strategy()
    metrics_strategy = di_container.infra_container.metrics_strategy()
    logging_strategy.log_error.assert_called_once()
    metrics_strategy.record_request.assert_called_once()

    _args, kwargs = metrics_strategy.record_request.call_args
    assert kwargs["status"] == "error"
    assert kwargs["error_type"] == "business"


def test_monitor_sync_error_infrastructure(di_container: AppContainer) -> None:
    # Arrange
    @monitor(event_name="infra_test")
    def sync_fail():
        raise InfrastructureError("db fail")

    # Act
    with pytest.raises(InfrastructureError):
        sync_fail()

    # Assert
    metrics_strategy = di_container.infra_container.metrics_strategy()
    _args, kwargs = metrics_strategy.record_request.call_args
    assert kwargs["error_type"] == "infrastructure"


def test_monitor_sync_suppress_exception() -> None:
    # Arrange
    @monitor(event_name="suppress", reraise=False)
    def sync_fail():
        raise ValueError("boom")

    # Act
    result = sync_fail()

    # Assert
    assert result is None


def test_monitor_callback_error(di_container: AppContainer) -> None:
    # Test that exception in callback is suppressed
    callback = MagicMock(side_effect=ValueError("Callback failed"))

    @monitor(
        Events.SEARCH_SERVICE,
        action_when_exception=callback,
        reraise=False,
    )
    def func():
        raise RuntimeError("Original error")

    # Should not raise
    func()

    callback.assert_called_once()  # Should return None if suppressed
    logging_strategy = di_container.infra_container.logging_strategy()
    logging_strategy.log_error.assert_called_once()


# --- Async Tests ---
@pytest.mark.asyncio
async def test_monitor_async_success(di_container: AppContainer) -> None:
    # Arrange
    @monitor(event_name="async_test")
    async def async_func(x):
        return x * 2

    # Act
    result = await async_func(5)

    # Assert
    assert result == 10
    metrics_strategy = di_container.infra_container.metrics_strategy()
    metrics_strategy.record_request.assert_called_once()
    assert metrics_strategy.record_request.call_args[1]["status"] == "success"


@pytest.mark.asyncio
async def test_monitor_async_error(di_container: AppContainer) -> None:
    # Arrange
    @monitor(event_name="async_error")
    async def async_fail():
        raise ValueError("async boom")

    # Act
    with pytest.raises(ValueError, match="async boom"):
        await async_fail()

    # Assert
    metrics_strategy = di_container.infra_container.metrics_strategy()
    metrics_strategy.record_request.assert_called_once()
    assert metrics_strategy.record_request.call_args[1]["status"] == "error"


@pytest.mark.asyncio
async def test_monitor_async_suppress_returns_none() -> None:
    """Async monitor with reraise=False returns None on exception."""

    @monitor(event_name="async_suppress", reraise=False)
    async def async_fail():
        raise RuntimeError("suppressed")

    result = await async_fail()
    assert result is None
