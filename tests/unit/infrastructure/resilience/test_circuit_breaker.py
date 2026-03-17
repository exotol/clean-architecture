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
    cb = CircuitBreaker(config_disabled, name="test")
    func = AsyncMock(return_value=42)
    result = await cb.call(func, "a", b=2)
    assert result == 42
    func.assert_called_once_with("a", b=2)


@pytest.mark.asyncio
async def test_call_success_when_closed(
    config_enabled: CircuitBreakerConfig,
) -> None:
    """When closed, successful call returns result."""
    cb = CircuitBreaker(config_enabled, name="test")
    func = AsyncMock(return_value="ok")
    result = await cb.call(func)
    assert result == "ok"


@pytest.mark.asyncio
async def test_call_failure_increments_and_raises(
    config_enabled: CircuitBreakerConfig,
) -> None:
    """When closed, failure raises and increments count."""
    cb = CircuitBreaker(config_enabled, name="test")
    func = AsyncMock(side_effect=ValueError("fail"))
    with pytest.raises(ValueError, match="fail"):
        await cb.call(func)
    func.assert_called_once()


@pytest.mark.asyncio
async def test_call_opens_after_threshold(
    config_enabled: CircuitBreakerConfig,
) -> None:
    """After failure_threshold failures, circuit opens and call raises."""
    cb = CircuitBreaker(config_enabled, name="test")
    func = AsyncMock(side_effect=RuntimeError("err"))
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
    cb = CircuitBreaker(config_enabled, name="test")
    func_fail = AsyncMock(side_effect=ValueError("x"))
    for _ in range(2):
        with pytest.raises(ValueError, match="x"):
            await cb.call(func_fail)
    # Now open. Wait for recovery.
    await asyncio.sleep(config_enabled.recovery_timeout_seconds + 0.1)
    func_ok = AsyncMock(return_value=99)
    result = await cb.call(func_ok)
    assert result == 99
    # Next call should still work (closed again).
    result2 = await cb.call(AsyncMock(return_value=100))
    assert result2 == 100
