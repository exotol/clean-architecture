from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

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
from app.presentation.api.exception_handlers import (
    business_error_handler,
    global_exception_handler,
    infra_error_handler,
    request_validation_handler,
)
from app.utils.configs import SecurityConfig, ProfilingConfig
from app.utils.configs import load_settings
from app.utils.serializer import AdvORJSONResponse


def create_middleware_list(
    security_config: SecurityConfig = Provide[
        AppContainer.infra_container.security_config
    ],
    profiling_config: ProfilingConfig = Provide[
        AppContainer.infra_container.profiling_config
    ]
) -> list[Middleware]:
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
        middleware_list.append(Middleware(
            ProfilingMiddleware,
            config=profiling_config
        ))

    return middleware_list


def add_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(InfrastructureError, infra_error_handler)
    app.add_exception_handler(BusinessError, business_error_handler)
    app.add_exception_handler(RequestValidationError, request_validation_handler)
    app.add_exception_handler(Exception, global_exception_handler)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager."""
    # Startup
    container: AppContainer = app.state.container
    init_result = container.init_resources()
    if init_result is not None:
        await init_result
    yield
    # Shutdown
    shutdown_result = container.shutdown_resources()
    if shutdown_result is not None:
        await shutdown_result


def create_app() -> FastAPI:
    """
    Factory function to create the FastAPI application.
    """
    container: AppContainer = AppContainer()
    container.infra_container.config.from_dict(load_settings().as_dict())

    logger_config = container.infra_container.logger_config()
    otlp_config = container.infra_container.otlp_config()

    setup_logging()
    setup_metrics()

    app = FastAPI(
        middleware=create_middleware_list(),
        lifespan=lifespan,
        default_response_class=AdvORJSONResponse,
    )

    # Store container in app state for lifespan access
    app.state.container = container

    app.include_router(create_main_router())
    add_exception_handlers(app)
    return app
