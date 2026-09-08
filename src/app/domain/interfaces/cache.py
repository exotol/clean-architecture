from __future__ import annotations

from abc import ABC
from abc import abstractmethod


class ICacheBackend(ABC):
    """Interface for cache backend (in-memory or external)."""

    @abstractmethod
    def get(self, key: str) -> str | None:
        """Get value by key. Returns None if missing or expired."""

    @abstractmethod
    def set(
        self,
        key: str,
        value: str,
        ttl_seconds: int | None = None,
    ) -> None:
        """Set value with optional TTL."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete key."""
