"""Unit tests for InMemoryCacheBackend."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from app.infrastructure.cache.memory import InMemoryCacheBackend
from app.utils.configs import CacheConfig


@pytest.fixture
def config() -> CacheConfig:
    """Cache config with short TTL and small size for tests."""
    return CacheConfig(ttl_seconds=60, max_size=3)


@pytest.fixture
def backend(config: CacheConfig) -> InMemoryCacheBackend:
    """In-memory cache backend instance."""
    return InMemoryCacheBackend(config)


def test_get_missing_returns_none(backend: InMemoryCacheBackend) -> None:
    """Get for missing key returns None."""
    assert backend.get("missing") is None


def test_set_and_get(backend: InMemoryCacheBackend) -> None:
    """Set then get returns the value."""
    backend.set("k", "v")
    assert backend.get("k") == "v"


def test_get_expired_returns_none(
    backend: InMemoryCacheBackend,
    config: CacheConfig,
) -> None:
    """Get after TTL expires returns None."""
    backend.set("k", "v")
    with patch("app.infrastructure.cache.memory.time.monotonic") as m:
        m.return_value = 0.0
        backend.set("k", "v")
        m.return_value = config.ttl_seconds + 1
        assert backend.get("k") is None


def test_set_with_custom_ttl(backend: InMemoryCacheBackend) -> None:
    """Set with ttl_seconds overrides default."""
    backend.set("k", "v", ttl_seconds=10)
    assert backend.get("k") == "v"


def test_set_updates_existing_key(backend: InMemoryCacheBackend) -> None:
    """Set for existing key updates value and moves to end."""
    backend.set("k", "v1")
    backend.set("k", "v2")
    assert backend.get("k") == "v2"


def test_lru_eviction_when_over_max_size(
    backend: InMemoryCacheBackend,
    config: CacheConfig,
) -> None:
    """When max_size exceeded, oldest item is evicted."""
    assert config.max_size == 3
    backend.set("a", "1")
    backend.set("b", "2")
    backend.set("c", "3")
    backend.set("d", "4")
    assert backend.get("a") is None
    assert backend.get("b") == "2"
    assert backend.get("c") == "3"
    assert backend.get("d") == "4"


def test_delete_existing_key(backend: InMemoryCacheBackend) -> None:
    """Delete removes the key."""
    backend.set("k", "v")
    backend.delete("k")
    assert backend.get("k") is None


def test_delete_missing_key_no_op(backend: InMemoryCacheBackend) -> None:
    """Delete for missing key does nothing."""
    backend.delete("missing")
    assert backend.get("missing") is None
