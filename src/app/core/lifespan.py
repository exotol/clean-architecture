from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import load_settings
from app.core.containers import AppContainer
from app.core.logging import setup_logging


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:  # noqa RUF029
    container: AppContainer = AppContainer()
    container.config_container.config.from_dict(load_settings().as_dict())
    setup_logging()

    yield

    container.unwire()
