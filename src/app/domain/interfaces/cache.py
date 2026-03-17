from __future__ import annotations

from typing import Protocol
from typing import runtime_checkable


@runtime_checkable
class ICacheBackend(Protocol):
    """Interface for cache backend (in-memory or external)."""

    def get(self, key: str) -> str | None:
        """Get value by key. Returns None if missing or expired."""
        ...

    def set(
        self,
        key: str,
        value: str,
        ttl_seconds: int | None = None,
    ) -> None:
        """Set value with optional TTL."""
        ...

    def delete(self, key: str) -> None:
        """Delete key."""
        ...
