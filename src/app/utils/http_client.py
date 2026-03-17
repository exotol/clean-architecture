"""HTTP-клиент (httpx) как ресурс DI.

Создание/закрытие - только через DI-контейнер.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from dependency_injector import resources
import httpx


if TYPE_CHECKING:
    from app.utils.configs import HttpClientConfig


def _create_client(
    config: HttpClientConfig,
    transport: httpx.AsyncBaseTransport | None = None,
) -> httpx.AsyncClient:
    """Собрать AsyncClient из конфига.

    transport задается только для тестов.
    """
    timeout = httpx.Timeout(config.timeout_seconds)
    limits = httpx.Limits(
        max_connections=config.max_connections,
        max_keepalive_connections=config.max_keepalive_connections,
        keepalive_expiry=config.keepalive_expiry_seconds,
    )
    return httpx.AsyncClient(
        base_url=config.base_url,
        timeout=timeout,
        limits=limits,
        transport=transport,
    )


class HttpClientResource(resources.AsyncResource[httpx.AsyncClient]):
    """Ресурс DI: создаёт httpx.AsyncClient при init.

    И закрывает при shutdown.
    """

    async def init(
        self,
        config: HttpClientConfig,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> httpx.AsyncClient:
        """Создать и вернуть клиент (config и transport приходят из DI)."""
        client = _create_client(config, transport=transport)
        _ = id(self)
        return client

    async def shutdown(
        self,
        client: httpx.AsyncClient | None,
    ) -> None:
        """Закрыть клиент при остановке контейнера."""
        if client is not None:
            _ = id(self)
            await client.aclose()
