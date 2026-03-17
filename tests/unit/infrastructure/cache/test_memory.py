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
    # Arrange

    # Act
    actual = backend.get("missing")

    # Assert
    assert actual is None, (
        f"Expected missing key to return None, got {actual!r}"
    )


def test_set_and_get(backend: InMemoryCacheBackend) -> None:
    """Set then get returns the value."""
    # Arrange
    backend.set("k", "v")

    # Act
    actual = backend.get("k")

    # Assert
    assert actual == "v", f"Expected get('k') to return 'v', got {actual!r}"


def test_get_expired_returns_none(
    backend: InMemoryCacheBackend,
    config: CacheConfig,
) -> None:
    """Get after TTL expires returns None."""
    # Arrange
    with patch("app.infrastructure.cache.memory.time.monotonic") as m:
        m.return_value = 0.0
        backend.set("k", "v")
        m.return_value = config.ttl_seconds + 1

        # Act
        actual = backend.get("k")

        # Assert
        assert actual is None, (
            f"Expected expired key to return None, got {actual!r}"
        )


def test_set_with_custom_ttl(backend: InMemoryCacheBackend) -> None:
    """Set with ttl_seconds overrides default."""
    # Arrange
    backend.set("k", "v", ttl_seconds=10)

    # Act
    actual = backend.get("k")

    # Assert
    assert actual == "v", (
        f"Expected get('k') to return 'v' after set with ttl, got {actual!r}"
    )


def test_set_updates_existing_key(backend: InMemoryCacheBackend) -> None:
    """Set for existing key updates value and moves to end."""
    # Arrange
    backend.set("k", "v1")
    backend.set("k", "v2")

    # Act
    actual = backend.get("k")

    # Assert
    assert actual == "v2", (
        f"Expected updated key to return 'v2', got {actual!r}"
    )


def test_lru_eviction_when_over_max_size(
    backend: InMemoryCacheBackend,
    config: CacheConfig,
) -> None:
    """When max_size exceeded, oldest item is evicted."""
    # Arrange
    assert config.max_size == 3, (
        f"Test expects max_size=3, got {config.max_size}"
    )
    backend.set("a", "1")
    backend.set("b", "2")
    backend.set("c", "3")

    # Act
    backend.set("d", "4")

    # Assert
    assert backend.get("a") is None, "Expected oldest key 'a' to be evicted"
    assert backend.get("b") == "2", (
        f"Expected 'b' to remain in cache, got {backend.get('b')!r}"
    )
    assert backend.get("c") == "3", (
        f"Expected 'c' to remain in cache, got {backend.get('c')!r}"
    )
    assert backend.get("d") == "4", (
        f"Expected newest key 'd' to be present, got {backend.get('d')!r}"
    )


def test_delete_existing_key(backend: InMemoryCacheBackend) -> None:
    """Delete removes the key."""
    # Arrange
    backend.set("k", "v")

    # Act
    backend.delete("k")
    actual = backend.get("k")

    # Assert
    assert actual is None, (
        f"Expected deleted key to return None, got {actual!r}"
    )


def test_delete_missing_key_no_op(backend: InMemoryCacheBackend) -> None:
    """Delete for missing key does nothing."""
    # Arrange

    # Act
    backend.delete("missing")
    actual = backend.get("missing")

    # Assert
    assert actual is None, (
        "Expected missing key after delete() to still return None, "
        f"got {actual!r}"
    )
