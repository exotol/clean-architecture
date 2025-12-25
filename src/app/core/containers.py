from dependency_injector import containers
from dependency_injector import providers
from granian import Granian
from granian.constants import Interfaces

from app.application.services.search_service import SearchService
from app.infrastructure.persistence.repositories.search_repository import (
    SearchRepository,
)
from app.infrastructure.services.metrics_service import MetricsService
from app.utils.configs import LoggerConfig
from app.utils.configs import ServerConfig


class InfrastructureContainer(containers.DeclarativeContainer):
    config = providers.Configuration()

    server_config = providers.Singleton(
        ServerConfig,
        host=config.GRANIAN.SERVER.HOST,
        port=config.GRANIAN.SERVER.PORT.as_int(),
        workers=config.GRANIAN.SERVER.WORKERS.as_int(),
        reload=config.GRANIAN.SERVER.RELOAD,
        target_run=config.GRANIAN.SERVER.TARGET_RUN,
        factory=config.GRANIAN.SERVER.FACTORY,
        log_level=config.GRANIAN.SERVER.LOG_LEVEL,
        log_access=config.GRANIAN.SERVER.LOG_ACCESS,
    )

    logger_config = providers.Singleton(
        LoggerConfig,
        level=config.LOGGING.LEVEL,
        format=config.LOGGING.FORMAT,
        path=config.LOGGING.PATH,
        rotation=config.LOGGING.ROTATION,
        retention=config.LOGGING.RETENTION,
        loggers_to_root=config.LOGGING.LOGGERS_TO_ROOT,
    )

    metrics_service = providers.Singleton(MetricsService)


class ServerContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        packages=["__main__", "app"]
    )
    infra_container = providers.Container(InfrastructureContainer)

    granian_server = providers.Singleton(
        Granian,
        target=infra_container.server_config.provided.target_run,
        address=infra_container.server_config.provided.host,
        port=infra_container.server_config.provided.port,
        interface=Interfaces.ASGI,
        workers=infra_container.server_config.provided.workers,
        reload=infra_container.server_config.provided.reload,
        factory=infra_container.server_config.provided.factory,
        log_level=infra_container.server_config.provided.log_level,
        log_access=infra_container.server_config.provided.log_access,
        log_dictconfig={},
    )


class AppContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(packages=["app"])
    infra_container = providers.Container(InfrastructureContainer)

    search_repository = providers.Singleton(SearchRepository)

    search_service = providers.Singleton(
        SearchService,
        repository=search_repository,
    )
