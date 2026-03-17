from __future__ import annotations

from typing import TYPE_CHECKING

from httpx import ASGITransport
from httpx import AsyncClient
import pytest

from app.core.app_factory import create_app


if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from fastapi import FastAPI


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture(scope="session")
def app() -> FastAPI:
    return create_app()


@pytest.fixture(scope="session")
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c
