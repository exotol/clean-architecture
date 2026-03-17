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
    allowed, retry_after = await store.check_and_record(
        "client1",
        limit=2,
        window_seconds=10.0,
    )
    assert allowed is True
    assert retry_after == 0.0
    allowed2, _ = await store.check_and_record(
        "client1",
        limit=2,
        window_seconds=10.0,
    )
    assert allowed2 is True


@pytest.mark.asyncio
async def test_store_denies_over_limit(store: RateLimitStore) -> None:
    """check_and_record denies when over limit and returns retry_after."""
    for _ in range(2):
        await store.check_and_record("client1", limit=2, window_seconds=10.0)
    allowed, retry_after = await store.check_and_record(
        "client1",
        limit=2,
        window_seconds=10.0,
    )
    assert allowed is False
    assert retry_after > 0


@pytest.mark.asyncio
async def test_middleware_disabled_passes_through(
    config_disabled: RateLimitConfig,
) -> None:
    """When disabled, request is passed to next."""
    app = MagicMock()
    middleware = RateLimitMiddleware(app, config_disabled, RateLimitStore())
    request = MagicMock()
    call_next = AsyncMock(return_value=MagicMock(status_code=200))
    response = await middleware.dispatch(request, call_next)
    call_next.assert_called_once_with(request)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_middleware_enabled_returns_429_when_over_limit(
    config_enabled: RateLimitConfig,
) -> None:
    """When over limit, returns 429 with Retry-After."""
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
    response = await middleware.dispatch(request, call_next)
    call_next.assert_not_called()
    assert response.status_code == 429
    assert "Retry-After" in response.headers


@pytest.mark.asyncio
async def test_get_client_key_from_header(
    config_with_header: RateLimitConfig,
) -> None:
    """Client key is taken from header when key_header is set."""
    app = MagicMock()
    store = RateLimitStore()
    middleware = RateLimitMiddleware(app, config_with_header, store)
    request = MagicMock()
    request.headers = {"X-Client-Id": "  client-123  "}
    request.client = None
    key = middleware._get_client_key(request)
    assert key == "client-123"


@pytest.mark.asyncio
async def test_get_client_key_from_ip(config_enabled: RateLimitConfig) -> None:
    """Client key falls back to client.host when no header."""
    app = MagicMock()
    middleware = RateLimitMiddleware(app, config_enabled, RateLimitStore())
    request = MagicMock()
    request.headers = {}
    request.client = MagicMock(host="10.0.0.1")
    key = middleware._get_client_key(request)
    assert key == "10.0.0.1"


@pytest.mark.asyncio
async def test_get_client_key_unknown_when_no_client(
    config_enabled: RateLimitConfig,
) -> None:
    """Client key is 'unknown' when client is None and no header."""
    app = MagicMock()
    middleware = RateLimitMiddleware(app, config_enabled, RateLimitStore())
    request = MagicMock()
    request.headers = {}
    request.client = None
    key = middleware._get_client_key(request)
    assert key == "unknown"
