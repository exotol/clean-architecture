from __future__ import annotations

from collections import OrderedDict
import time
from typing import TYPE_CHECKING

from app.domain.interfaces.cache import ICacheBackend


if TYPE_CHECKING:
    from app.utils.configs import CacheConfig


class InMemoryCacheBackend(ICacheBackend):
    """In-memory cache with TTL and max size (LRU eviction)."""

    def __init__(self, config: CacheConfig) -> None:
        self._ttl = config.ttl_seconds
        self._max_size = config.max_size
        self._store: OrderedDict[str, tuple[str, float]] = OrderedDict()

    def get(self, key: str) -> str | None:
        """Get value by key. Returns None if missing or expired."""
        if key not in self._store:
            return None
        value, expires_at = self._store[key]
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        self._store.move_to_end(key)
        return value

    def set(
        self,
        key: str,
        value: str,
        ttl_seconds: int | None = None,
    ) -> None:
        """Set value with optional TTL."""
        ttl = ttl_seconds if ttl_seconds is not None else self._ttl
        expires_at = time.monotonic() + ttl
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = (value, expires_at)
        while len(self._store) > self._max_size:
            self._store.popitem(last=False)

    def delete(self, key: str) -> None:
        """Delete key."""
        if key in self._store:
            del self._store[key]
