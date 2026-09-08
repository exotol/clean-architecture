from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING
from typing import TypeVar


if TYPE_CHECKING:
    from collections.abc import Awaitable
    from collections.abc import Callable


T = TypeVar("T")


class ICircuitBreaker(ABC):
    """Interface for circuit breaker wrapping async calls."""

    @abstractmethod
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
