from __future__ import annotations

import operator
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from app.core.events import Events
from app.core.exceptions import BusinessError
from app.core.exceptions import InfrastructureError
from app.utils.monitor import get_bound_arguments
from app.utils.monitor import monitor


if TYPE_CHECKING:
    from app.core.containers import AppContainer


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


# --- _get_bound_arguments ---
def test_get_bound_arguments_resolves_positional_and_keyword() -> None:
    # Arrange
    func = operator.add

    # Act
    out = get_bound_arguments(func, (1, 2), {})

    # Assert
    assert out == {"a": 1, "b": 2}, (
        f"Expected {{'a': 1, 'b': 2}}, got {out}"
    )


def test_get_bound_arguments_excludes_self() -> None:
    # Arrange: use unbound function with explicit "self" param
    def method(self: object, x: int) -> int:
        # Reference `self` so linters don't treat it as unused; return value
        # doesn't matter for this test because the function isn't executed.
        return x + hash(self) * 0

    # Act: bind (instance, 3) -> bound.arguments has self and x; we drop self
    out = get_bound_arguments(method, (object(), 3), {})

    # Assert
    assert "self" not in out, (f"Expected no 'self' in result, got {out}")
    assert out == {"x": 3}, (f"Expected {{'x': 3}}, got {out}")


def test_get_bound_arguments_bind_error_returns_empty() -> None:
    # Arrange: pass wrong number of args so bind fails
    func = operator.add

    # Act
    out = get_bound_arguments(func, (1,), {})

    # Assert
    assert out == {}, (f"Expected empty dict on bind error, got {out}")


# --- Sync Tests ---
def test_monitor_sync_success(
    di_container: AppContainer,
    mock_tracing_strategy: MagicMock,
) -> None:
    # Arrange
    @monitor(event_name="test_sync")
    def sync_func(a: int, b: int) -> int:
        return a + b

    # Act
    result = sync_func(1, 2)

    # Assert
    assert result == 3, (
        f"Expected sync_func(1, 2) = 3, got {result}"
    )
    logging_strategy = di_container.infra_container.logging_strategy()
    metrics_strategy = di_container.infra_container.metrics_strategy()
    mock_tracing_strategy.start_span.assert_called_once_with("test_sync")
    logging_strategy.log_start.assert_called_once()
    logging_strategy.log_success.assert_called_once()
    assert metrics_strategy.record_request.call_count == 1, (
        f"Expected record_request called once, "
        f"got {metrics_strategy.record_request.call_count}"
    )
    _args, kwargs = metrics_strategy.record_request.call_args
    assert kwargs["status"] == "success", (
        f"Expected status='success', got {kwargs.get('status')!r}"
    )
    assert kwargs["event_name"] == "test_sync", (
        f"Expected event_name='test_sync', got {kwargs.get('event_name')!r}"
    )


def test_monitor_sync_error(di_container: AppContainer) -> None:
    # Arrange
    @monitor(event_name=Events.SEARCH_SERVICE, reraise=True)
    def sync_fail() -> None:
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
    assert metrics_strategy.record_request.call_count == 1, (
        f"Expected record_request called once, "
        f"got {metrics_strategy.record_request.call_count}"
    )
    _args, kwargs = metrics_strategy.record_request.call_args
    assert kwargs["status"] == "error", (
        f"Expected status='error', got {kwargs.get('status')!r}"
    )
    assert kwargs["error_type"] == "business", (
        f"Expected error_type='business', got {kwargs.get('error_type')!r}"
    )


def test_monitor_sync_error_infrastructure(di_container: AppContainer) -> None:
    # Arrange
    @monitor(event_name="infra_test")
    def sync_fail() -> None:
        raise InfrastructureError("db fail")

    # Act
    with pytest.raises(InfrastructureError):
        sync_fail()

    # Assert
    metrics_strategy = di_container.infra_container.metrics_strategy()
    _args, kwargs = metrics_strategy.record_request.call_args
    assert kwargs["error_type"] == "infrastructure", (
        f"Expected error_type='infrastructure', "
        f"got {kwargs.get('error_type')!r}"
    )


def test_monitor_sync_suppress_exception() -> None:
    # Arrange
    @monitor(event_name="suppress", reraise=False)
    def sync_fail() -> None:
        raise ValueError("boom")

    # Act
    result = sync_fail()

    # Assert
    assert result is None, (
        f"Expected None when reraise=False, got {result!r}"
    )


def test_monitor_callback_error(di_container: AppContainer) -> None:
    # Arrange
    callback = MagicMock(side_effect=ValueError("Callback failed"))

    @monitor(
        Events.SEARCH_SERVICE,
        action_when_exception=callback,
        reraise=False,
    )
    def func() -> None:
        raise RuntimeError("Original error")

    # Act
    func()

    # Assert
    assert callback.call_count == 1, (
        f"Expected callback called once, got {callback.call_count}"
    )
    logging_strategy = di_container.infra_container.logging_strategy()
    logging_strategy.log_error.assert_called_once()


# --- Async Tests ---
@pytest.mark.asyncio
async def test_monitor_async_success(di_container: AppContainer) -> None:
    # Arrange
    @monitor(event_name="async_test")
    async def async_func(x: int) -> int:
        return x * 2

    # Act
    result = await async_func(5)

    # Assert
    assert result == 10, (
        f"Expected async_func(5) = 10, got {result}"
    )
    metrics_strategy = di_container.infra_container.metrics_strategy()
    assert metrics_strategy.record_request.call_count == 1, (
        f"Expected record_request called once, "
        f"got {metrics_strategy.record_request.call_count}"
    )
    call_kw = metrics_strategy.record_request.call_args[1]
    assert call_kw["status"] == "success", (
        "Expected status='success' in record_request kwargs"
    )


@pytest.mark.asyncio
async def test_monitor_async_error(di_container: AppContainer) -> None:
    # Arrange
    @monitor(event_name="async_error")
    async def async_fail() -> None:
        raise ValueError("async boom")

    # Act
    with pytest.raises(ValueError, match="async boom"):
        await async_fail()

    # Assert
    metrics_strategy = di_container.infra_container.metrics_strategy()
    assert metrics_strategy.record_request.call_count == 1, (
        f"Expected record_request called once, "
        f"got {metrics_strategy.record_request.call_count}"
    )
    assert metrics_strategy.record_request.call_args[1]["status"] == "error", (
        "Expected status='error' in record_request kwargs"
    )


@pytest.mark.asyncio
async def test_monitor_async_suppress_returns_none() -> None:
    # Arrange
    @monitor(event_name="async_suppress", reraise=False)
    async def async_fail() -> None:
        raise RuntimeError("suppressed")

    # Act
    result = await async_fail()

    # Assert
    assert result is None, (
        f"Expected None when reraise=False, got {result!r}"
    )
