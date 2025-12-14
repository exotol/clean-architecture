from dependency_injector import containers, providers
from granian import Granian
from granian.constants import Interfaces

from app.schemas.logger import LoggerConfig
from app.schemas.server import ServerConfig


class ConfigContainer(containers.DeclarativeContainer):
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


class ServerContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        packages=["__main__", "app"]
    )
    config_container = providers.Container(ConfigContainer)

    granian_server = providers.Singleton(
        Granian,
        target=config_container.server_config.provided.target_run,
        address=config_container.server_config.provided.host,
        port=config_container.server_config.provided.port,
        interface=Interfaces.ASGI,
        workers=config_container.server_config.provided.workers,
        reload=config_container.server_config.provided.reload,
        factory=config_container.server_config.provided.factory,
        log_level=config_container.server_config.provided.log_level,
        log_access=config_container.server_config.provided.log_access,
        log_dictconfig={},
    )


class AppContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(packages=["app"])
    config_container = providers.Container(ConfigContainer)
