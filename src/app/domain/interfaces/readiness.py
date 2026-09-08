from __future__ import annotations

from abc import ABC
from abc import abstractmethod


class IReadinessChecker(ABC):
    """Interface for readiness checks (dependencies available)."""

    @abstractmethod
    async def is_ready(self) -> bool:
        """Return True if the service is ready to accept traffic."""
