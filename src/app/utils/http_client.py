"""Единообразное создание HTTP-клиентов (httpx) из настроек."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

import httpx


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from app.utils.configs import HttpClientConfig


def create_async_client(
    config: HttpClientConfig,
    transport: httpx.AsyncBaseTransport | None = None,
) -> httpx.AsyncClient:
    """Создать AsyncClient с транспортом и таймаутами из конфига.

    Если передан transport (например ASGITransport для тестов),
    он используется; иначе — транспорт по умолчанию с limits из конфига.
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


@contextlib.asynccontextmanager
async def async_client_context(
    config: HttpClientConfig,
    transport: httpx.AsyncBaseTransport | None = None,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Контекстный менеджер: создаёт клиент и закрывает при выходе."""
    client = create_async_client(config, transport=transport)
    try:
        yield client
    finally:
        await client.aclose()
