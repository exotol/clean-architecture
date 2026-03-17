from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

import anyio
from asgi_correlation_id import CorrelationIdMiddleware
from dependency_injector.wiring import Provide
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware import Middleware

from app.core.constants import TRACE_ID
from app.core.constants import VALIDATION_UUID_OFF
from app.core.containers import AppContainer
from app.core.exceptions import BusinessError
from app.core.exceptions import InfrastructureError
from app.infrastructure.observability.logging import setup_logging
from app.infrastructure.observability.metrics import setup_metrics
from app.infrastructure.observability.profiling import ProfilingMiddleware
from app.presentation.api.application_api import create_main_router
from app.presentation.exception_handlers import business_error_handler
from app.presentation.exception_handlers import global_exception_handler
from app.presentation.exception_handlers import infra_error_handler
from app.presentation.exception_handlers import request_validation_handler
from app.utils.configs import ProfilingConfig
from app.utils.configs import SecurityConfig
from app.utils.configs import load_settings
from app.utils.serializer import AdvORJSONResponse


if TYPE_CHECKING:
    from collections.abc import AsyncIterator


def create_middleware_list(
    security_config: SecurityConfig = Provide[
        AppContainer.infra_container.security_config
    ],
    profiling_config: ProfilingConfig = Provide[
        AppContainer.infra_container.profiling_config
    ],
) -> list[Middleware]:
    """Create the middleware list based on configuration."""
    middleware_list = [
        Middleware(
            CorrelationIdMiddleware,
            header_name=TRACE_ID,
            validator=VALIDATION_UUID_OFF,
        ),
        Middleware(
            TrustedHostMiddleware,
            allowed_hosts=security_config.trusted_hosts,
        ),
        Middleware(
            CORSMiddleware,
            allow_origins=security_config.cors_origins,
            allow_credentials=security_config.cors_allow_credentials,
            allow_methods=security_config.cors_allow_methods,
            allow_headers=security_config.cors_allow_headers,
        ),
    ]
    if profiling_config.enabled:
        middleware_list.append(
            Middleware(
                ProfilingMiddleware,  # type: ignore[arg-type]
                config=profiling_config,
            ),
        )

    return middleware_list


def add_exception_handlers(app: FastAPI) -> None:
    """Register exception handlers on the FastAPI app."""
    app.add_exception_handler(InfrastructureError, infra_error_handler)
    app.add_exception_handler(BusinessError, business_error_handler)
    app.add_exception_handler(
        RequestValidationError, request_validation_handler,
    )
    app.add_exception_handler(Exception, global_exception_handler)


def create_app() -> FastAPI:
    """Factory function to create the FastAPI application."""
    container: AppContainer = AppContainer()
    container.infra_container.config.from_dict(  # type: ignore[attr-defined]
        load_settings().as_dict(),
    )

    logger_config = container.infra_container.logger_config()
    otlp_config = container.infra_container.otlp_config()

    setup_logging(logger_config=logger_config, otlp_config=otlp_config)
    setup_metrics()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.container = container
        container.wire(packages=["app"])
        try:
            await anyio.lowlevel.checkpoint()
            yield
        finally:
            container.unwire()

    app = FastAPI(
        middleware=create_middleware_list(),
        lifespan=lifespan,
        default_response_class=AdvORJSONResponse,
    )
    app.state.container = container

    app.include_router(create_main_router())
    add_exception_handlers(app)
    return app
