from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.containers import AppContainer
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:  # noqa RUF029
    container: AppContainer = AppContainer()
    setup_logging()
    container.wire(packages=["app"])

    yield

    container.unwire()
