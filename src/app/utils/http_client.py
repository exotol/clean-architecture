"""HTTP-клиент (httpx) как ресурс DI: создание и закрытие только через контейнер."""

from __future__ import annotations

import httpx
from dependency_injector import resources

from app.utils.configs import HttpClientConfig


def _create_client(
    config: HttpClientConfig,
    transport: httpx.AsyncBaseTransport | None = None,
) -> httpx.AsyncClient:
    """Собрать AsyncClient из конфига и опционального транспорта (внутренний)."""
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
    """Ресурс DI: создаёт httpx.AsyncClient при init, закрывает при shutdown."""

    async def init(
        self,
        config: HttpClientConfig,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> httpx.AsyncClient:
        """Создать и вернуть клиент; конфиг и транспорт инжектируются из контейнера."""
        return _create_client(config, transport=transport)

    async def shutdown(
        self,
        client: httpx.AsyncClient | None,
    ) -> None:
        """Закрыть клиент при остановке контейнера."""
        if client is not None:
            await client.aclose()
