from asgi_correlation_id import CorrelationIdMiddleware
from dependency_injector.wiring import Provide
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware import Middleware

from app.core.constants import TRACE_ID, VALIDATION_UUID_OFF
from app.core.containers import AppContainer
from app.core.exceptions import BusinessError, InfrastructureError
from app.infrastructure.observability.logging import setup_logging
from app.infrastructure.observability.metrics import setup_metrics
from app.presentation.api.application_api import create_main_router
from app.presentation.api.exception_handlers import (
    global_exception_handler,
    infra_error_handler,
    business_error_handler
)
from app.utils.configs import SecurityConfig
from app.utils.configs import load_settings


def create_middleware_list(
    security_config: SecurityConfig = Provide[
        AppContainer.infra_container.security_config]
) -> list[Middleware]:
    return [
        Middleware(
            CorrelationIdMiddleware,
            # Указываем имя хедера, который мы
            # ждем от клиента (или генерируем)
            header_name=TRACE_ID,
            # Опционально: отключаем валидацию UUID,
            # если ID имеют другой формат
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
        )
    ]


def add_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(InfrastructureError, infra_error_handler)
    app.add_exception_handler(BusinessError, business_error_handler)
    app.add_exception_handler(Exception, global_exception_handler)


def create_app() -> FastAPI:
    """
    Factory function to create the FastAPI application.
    """
    container: AppContainer = AppContainer()
    settings = load_settings()
    container.infra_container.config.from_dict(settings.as_dict())
    setup_logging()
    setup_metrics()
    app = FastAPI(
        middleware=create_middleware_list(),
        on_startup=[container.init_resources],
        on_shutdown=[container.shutdown_resources],
    )

    app.include_router(create_main_router())
    add_exception_handlers(app)
    return app
