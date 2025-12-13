from typing import Any, cast

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.middleware import Middleware

from app.core.lifespan import lifespan as fn_lifespan


def create_middleware_list() -> list[Middleware]:
    return [Middleware(cast("Any", CorrelationIdMiddleware))]


def create_app() -> FastAPI:
    return FastAPI(lifespan=fn_lifespan, middlewares=create_middleware_list())
