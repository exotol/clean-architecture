from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.utils.configs import HttpClientConfig
from app.utils.http_client import HttpClientResource


if TYPE_CHECKING:
    from httpx import AsyncClient


@pytest.mark.anyio
async def test_http_client_resource_init_and_shutdown() -> None:
    # Arrange
    config = HttpClientConfig(
        base_url="http://example.local",
        timeout_seconds=10.0,
        max_connections=5,
        max_keepalive_connections=2,
        keepalive_expiry_seconds=3.0,
    )
    resource = HttpClientResource()

    # Act
    client: AsyncClient = await resource.init(config)
    await resource.shutdown(client)

    # Assert
    assert str(client.base_url) == config.base_url, (
        f"Expected base_url={config.base_url!r}, got {client.base_url!r}"
    )
    assert client.is_closed is True, (
        "Expected AsyncClient to be closed after shutdown()"
    )


@pytest.mark.anyio
async def test_http_client_resource_shutdown_accepts_none() -> None:
    # Arrange
    resource = HttpClientResource()
    # Act
    await resource.shutdown(None)
    # Assert
    assert resource is not None, (
        "HttpClientResource.shutdown(None) should not raise"
    )
