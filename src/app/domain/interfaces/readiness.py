from __future__ import annotations

from typing import Protocol
from typing import runtime_checkable


@runtime_checkable
class IReadinessChecker(Protocol):
    """Interface for readiness checks (dependencies available)."""

    async def is_ready(self) -> bool:
        """Return True if the service is ready to accept traffic."""
        ...
