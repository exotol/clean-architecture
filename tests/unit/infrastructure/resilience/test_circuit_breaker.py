"""Unit tests for CircuitBreaker."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from app.infrastructure.resilience.circuit_breaker import CircuitBreaker
from app.utils.configs import CircuitBreakerConfig


@pytest.fixture
def config_enabled() -> CircuitBreakerConfig:
    """Circuit breaker enabled with low threshold."""
    return CircuitBreakerConfig(
        enabled=True,
        failure_threshold=2,
        recovery_timeout_seconds=1.0,
    )


@pytest.fixture
def config_disabled() -> CircuitBreakerConfig:
    """Circuit breaker disabled."""
    return CircuitBreakerConfig(
        enabled=False,
        failure_threshold=2,
        recovery_timeout_seconds=1.0,
    )


@pytest.mark.asyncio
async def test_call_when_disabled_passes_through(
    config_disabled: CircuitBreakerConfig,
) -> None:
    """When disabled, call executes func and returns result."""
    # Arrange
    cb = CircuitBreaker(config_disabled, name="test")
    func = AsyncMock(return_value=42)

    # Act
    result = await cb.call(func, "a", b=2)

    # Assert
    assert result == 42, (
        f"Expected cb.call to return 42 when disabled, got {result!r}"
    )
    func.assert_called_once_with("a", b=2)


@pytest.mark.asyncio
async def test_call_success_when_closed(
    config_enabled: CircuitBreakerConfig,
) -> None:
    """When closed, successful call returns result."""
    # Arrange
    cb = CircuitBreaker(config_enabled, name="test")
    func = AsyncMock(return_value="ok")

    # Act
    result = await cb.call(func)

    # Assert
    assert result == "ok", (
        f"Expected cb.call to return 'ok' on success, got {result!r}"
    )


@pytest.mark.asyncio
async def test_call_failure_increments_and_raises(
    config_enabled: CircuitBreakerConfig,
) -> None:
    """When closed, failure raises and increments count."""
    # Arrange
    cb = CircuitBreaker(config_enabled, name="test")
    func = AsyncMock(side_effect=ValueError("fail"))

    # Act / Assert
    with pytest.raises(ValueError, match="fail"):
        await cb.call(func)
    func.assert_called_once()


@pytest.mark.asyncio
async def test_call_opens_after_threshold(
    config_enabled: CircuitBreakerConfig,
) -> None:
    """After failure_threshold failures, circuit opens and call raises."""
    # Arrange
    cb = CircuitBreaker(config_enabled, name="test")
    func = AsyncMock(side_effect=RuntimeError("err"))

    # Act / Assert
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await cb.call(func)
    with pytest.raises(RuntimeError, match="Circuit breaker 'test' is open"):
        await cb.call(AsyncMock(return_value=1))


@pytest.mark.asyncio
async def test_call_half_open_after_timeout_then_success(
    config_enabled: CircuitBreakerConfig,
) -> None:
    """After recovery_timeout, circuit goes half-open; success closes it."""
    # Arrange
    cb = CircuitBreaker(config_enabled, name="test")
    func_fail = AsyncMock(side_effect=ValueError("x"))
    for _ in range(2):
        with pytest.raises(ValueError, match="x"):
            await cb.call(func_fail)
    # Now open. Wait for recovery.
    await asyncio.sleep(config_enabled.recovery_timeout_seconds + 0.1)
    func_ok = AsyncMock(return_value=99)

    # Act
    result = await cb.call(func_ok)

    # Assert
    assert result == 99, (
        f"Expected half-open success to return 99, got {result!r}"
    )
    # Next call should still work (closed again).
    # Act
    result2 = await cb.call(AsyncMock(return_value=100))
    # Assert
    assert result2 == 100, (
        f"Expected circuit to be closed after success, got {result2!r}"
    )
