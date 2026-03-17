from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Protocol
from typing import TypeVar
from typing import runtime_checkable


if TYPE_CHECKING:
    from collections.abc import Awaitable
    from collections.abc import Callable


T = TypeVar("T")


@runtime_checkable
class ICircuitBreaker(Protocol):
    """Interface for circuit breaker wrapping async calls."""

    async def call(
        self,
        func: Callable[..., Awaitable[T]],
        *args: object,
        **kwargs: object,
    ) -> T:
        """Execute func(*args, **kwargs) with circuit breaker.

        Raises:
            Exception: When circuit is open or when func raises.
        """
        ...
