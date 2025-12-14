from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.middleware import Middleware

from app.core.config import load_settings
from app.core.containers import AppContainer
from app.core.logging import setup_logging


def create_middleware_list() -> list[Middleware]:
    return [Middleware(CorrelationIdMiddleware)]


def create_app() -> FastAPI:
    container: AppContainer = AppContainer()
    container.config_container.config.from_dict(load_settings().as_dict())
    setup_logging()
    return FastAPI(
        middlewares=create_middleware_list(),
        on_startup=[container.init_resources],
        on_shutdown=[container.shutdown_resources],
    )
