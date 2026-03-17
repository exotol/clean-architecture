from __future__ import annotations

import asyncio
from enum import Enum
import logging
import time
from typing import TYPE_CHECKING
from typing import TypeVar

from app.domain.interfaces.circuit_breaker import ICircuitBreaker


if TYPE_CHECKING:
    from collections.abc import Awaitable
    from collections.abc import Callable

    from app.utils.configs import CircuitBreakerConfig


T = TypeVar("T")
logger = logging.getLogger(__name__)


class _State(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker(ICircuitBreaker):
    """In-memory circuit breaker for async calls.

    State is held in instance (injected via DI).
    """

    def __init__(
        self,
        config: CircuitBreakerConfig,
        name: str = "default",
    ) -> None:
        self._config = config
        self._name = name
        self._state = _State.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._lock: asyncio.Lock = asyncio.Lock()

    async def call(
        self,
        func: Callable[..., Awaitable[T]],
        *args: object,
        **kwargs: object,
    ) -> T:
        """Execute func with circuit breaker. Raises when circuit is open."""
        if not self._config.enabled:
            return await func(*args, **kwargs)

        async with self._lock:
            if self._state == _State.OPEN:
                if time.monotonic() - self._last_failure_time >= (
                    self._config.recovery_timeout_seconds
                ):
                    self._state = _State.HALF_OPEN
                else:
                    raise RuntimeError(
                        f"Circuit breaker '{self._name}' is open",
                    ) from None

        try:
            result = await func(*args, **kwargs)
        except Exception as exc:
            await self._record_failure()
            raise exc from exc

        async with self._lock:
            if self._state == _State.HALF_OPEN:
                self._state = _State.CLOSED
                self._failure_count = 0
        return result

    async def _record_failure(self) -> None:
        """Update failure count and possibly open circuit."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            if self._failure_count >= self._config.failure_threshold:
                self._state = _State.OPEN
                logger.warning(
                    "Circuit breaker '%s' opened after %d failures",
                    self._name,
                    self._failure_count,
                )
