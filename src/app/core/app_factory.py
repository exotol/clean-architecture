from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI
from fastapi.middleware import Middleware

from app.core.constants import (
    TRACE_ID,
    VALIDATION_UUID_OFF,
)
from app.core.containers import AppContainer
from app.core.exceptions import (
    BusinessException,
    InfrastructureException,
)
from app.infrastructure.observability.logging import setup_logging
from app.presentation.api.application_api import create_main_router
from app.presentation.api.exception_handlers import (
    business_exception_handler,
    global_exception_handler,
    infrastructure_handler,
)
from app.utils.configs import load_settings


def create_middleware_list() -> list[Middleware]:
    return [
        Middleware(
            CorrelationIdMiddleware,
            # Указываем имя хедера, который мы
            # ждем от клиента (или генерируем)
            header_name=TRACE_ID,
            # Опционально: отключаем валидацию UUID,
            # если ID имеют другой формат
            validator=VALIDATION_UUID_OFF,
        )
    ]


def create_app() -> FastAPI:
    container: AppContainer = AppContainer()
    container.infra_container.config.from_dict(load_settings().as_dict())
    setup_logging()
    app = FastAPI(
        middleware=create_middleware_list(),
        on_startup=[container.init_resources],
        on_shutdown=[container.shutdown_resources],
    )
    app.include_router(create_main_router())
    app.add_exception_handler(InfrastructureException, infrastructure_handler)
    app.add_exception_handler(BusinessException, business_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)
    return app
