from __future__ import annotations

from typing import TYPE_CHECKING

from dependency_injector import providers
from dependency_injector import resources
from httpx import ASGITransport
from httpx import AsyncClient
import pytest

from app.core.app_factory import create_app
from app.utils.configs import get_http_client_config
from app.utils.http_client import _create_client


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from fastapi import FastAPI


class TestHttpClientResource(resources.AsyncResource):
    """Ресурс для тестов: клиент с ASGITransport(app)."""

    async def init(self, app: FastAPI) -> AsyncClient:
        """Создать клиент с транспортом ASGITransport(app)."""
        config = get_http_client_config().model_copy(
            update={"base_url": "http://test"},
        )
        return _create_client(config, transport=ASGITransport(app=app))

    async def shutdown(self, client: AsyncClient | None) -> None:
        """Закрыть клиент."""
        if client is not None:
            await client.aclose()


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def app() -> FastAPI:
    return create_app()


@pytest.fixture(scope="session")
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """HTTP-клиент из DI-контейнера; в тестах — override с ASGITransport(app)."""
    container = app.state.container
    infra = container.infra_container()
    infra.http_client.override(
        providers.Resource(TestHttpClientResource, app=app),
    )
    c = await infra.http_client()
    try:
        yield c
    finally:
        await infra.http_client.shutdown()
