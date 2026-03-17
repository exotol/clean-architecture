from __future__ import annotations

from typing import TYPE_CHECKING

from httpx import ASGITransport
import pytest

from app.core.app_factory import create_app
from app.utils.configs import get_http_client_config
from app.utils.http_client import async_client_context


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from fastapi import FastAPI
    from httpx import AsyncClient


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def app() -> FastAPI:
    return create_app()


@pytest.fixture(scope="session")
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """HTTP-клиент из единой фабрики; транспорт и таймауты из settings."""
    config = get_http_client_config().model_copy(
        update={"base_url": "http://test"},
    )
    async with async_client_context(
        config,
        transport=ASGITransport(app=app),
    ) as c:
        yield c
