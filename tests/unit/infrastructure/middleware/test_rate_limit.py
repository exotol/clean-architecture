"""Unit tests for RateLimitMiddleware and store."""

from __future__ import annotations

from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import pytest

from app.core.constants import TRACE_ID
from app.infrastructure.middleware.rate_limit import RateLimitMiddleware
from app.infrastructure.middleware.rate_limit import RateLimitStore
from app.utils.configs import RateLimitConfig


@pytest.fixture
def store() -> RateLimitStore:
    """Fresh in-memory rate limit store."""
    return RateLimitStore()


@pytest.fixture
def config_enabled() -> RateLimitConfig:
    """Rate limit enabled, 2 requests per 10s window."""
    return RateLimitConfig(
        enabled=True,
        requests_per_window=2,
        window_seconds=10.0,
        key_header=None,
    )


@pytest.fixture
def config_disabled() -> RateLimitConfig:
    """Rate limit disabled."""
    return RateLimitConfig(
        enabled=False,
        requests_per_window=10,
        window_seconds=10.0,
        key_header=None,
    )


@pytest.fixture
def config_with_header() -> RateLimitConfig:
    """Rate limit with key from header."""
    return RateLimitConfig(
        enabled=True,
        requests_per_window=1,
        window_seconds=10.0,
        key_header="X-Client-Id",
    )


@pytest.mark.asyncio
async def test_store_allows_under_limit(store: RateLimitStore) -> None:
    """check_and_record allows when under limit."""
    # Arrange

    # Act
    allowed, retry_after = await store.check_and_record(
        "client1",
        limit=2,
        window_seconds=10.0,
    )
    # Assert
    assert allowed is True, (
        f"Expected allowed=True under limit, got allowed={allowed}"
    )
    assert retry_after == 0.0, (
        f"Expected retry_after=0.0 when allowed, got retry_after={retry_after}"
    )
    # Act
    allowed2, _ = await store.check_and_record(
        "client1",
        limit=2,
        window_seconds=10.0,
    )
    # Assert
    assert allowed2 is True, (
        f"Expected second request under limit to be allowed, got {allowed2}"
    )


@pytest.mark.asyncio
async def test_store_denies_over_limit(store: RateLimitStore) -> None:
    """check_and_record denies when over limit and returns retry_after."""
    # Arrange
    for _ in range(2):
        await store.check_and_record("client1", limit=2, window_seconds=10.0)
    # Act
    allowed, retry_after = await store.check_and_record(
        "client1",
        limit=2,
        window_seconds=10.0,
    )
    # Assert
    assert allowed is False, (
        f"Expected allowed=False over limit, got allowed={allowed}"
    )
    assert retry_after > 0, (
        f"Expected retry_after>0 over limit, got retry_after={retry_after}"
    )


@pytest.mark.asyncio
async def test_middleware_disabled_passes_through(
    config_disabled: RateLimitConfig,
) -> None:
    """When disabled, request is passed to next."""
    # Arrange
    app = MagicMock()
    middleware = RateLimitMiddleware(app, config_disabled, RateLimitStore())
    request = MagicMock()
    call_next = AsyncMock(return_value=MagicMock(status_code=200))
    # Act
    response = await middleware.dispatch(request, call_next)
    call_next.assert_called_once_with(request)
    # Assert
    assert response.status_code == 200, (
        f"Expected pass-through response status_code=200, "
        f"got {response.status_code}"
    )


@pytest.mark.asyncio
async def test_middleware_enabled_returns_429_when_over_limit(
    config_enabled: RateLimitConfig,
) -> None:
    """When over limit, returns 429 with Retry-After."""
    # Arrange
    app = MagicMock()
    store = RateLimitStore()
    middleware = RateLimitMiddleware(app, config_enabled, store)
    for _ in range(3):
        await store.check_and_record("same-ip", limit=2, window_seconds=10.0)
    request = MagicMock()
    request.client = MagicMock(host="same-ip")
    request.state = MagicMock()
    setattr(request.state, TRACE_ID, None)
    request.headers = {}
    request.url = MagicMock(path="/api")
    call_next = AsyncMock()
    # Act
    response = await middleware.dispatch(request, call_next)
    call_next.assert_not_called()
    # Assert
    assert response.status_code == 429, (
        f"Expected status_code=429 when over limit, got {response.status_code}"
    )
    assert "Retry-After" in response.headers, (
        f"Expected Retry-After header in 429 response, "
        f"got headers={dict(response.headers)}"
    )


@pytest.mark.asyncio
async def test_get_client_key_from_header(
    config_with_header: RateLimitConfig,
) -> None:
    """Client key is taken from header when key_header is set."""
    # Arrange
    app = MagicMock()
    store = RateLimitStore()
    middleware = RateLimitMiddleware(app, config_with_header, store)
    request = MagicMock()
    request.headers = {"X-Client-Id": "  client-123  "}
    request.client = None
    # Act
    key = middleware._get_client_key(request)
    # Assert
    assert key == "client-123", (
        f"Expected header-derived key to be stripped, got {key!r}"
    )


@pytest.mark.asyncio
async def test_get_client_key_from_ip(config_enabled: RateLimitConfig) -> None:
    """Client key falls back to client.host when no header."""
    # Arrange
    app = MagicMock()
    middleware = RateLimitMiddleware(app, config_enabled, RateLimitStore())
    request = MagicMock()
    request.headers = {}
    request.client = MagicMock(host="10.0.0.1")
    # Act
    key = middleware._get_client_key(request)
    # Assert
    assert key == "10.0.0.1", f"Expected key to be client.host, got {key!r}"


@pytest.mark.asyncio
async def test_get_client_key_unknown_when_no_client(
    config_enabled: RateLimitConfig,
) -> None:
    """Client key is 'unknown' when client is None and no header."""
    # Arrange
    app = MagicMock()
    middleware = RateLimitMiddleware(app, config_enabled, RateLimitStore())
    request = MagicMock()
    request.headers = {}
    request.client = None
    # Act
    key = middleware._get_client_key(request)
    # Assert
    assert key == "unknown", (
        f"Expected key='unknown' when no header and no client, got {key!r}"
    )
