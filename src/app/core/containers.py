from dependency_injector import containers, providers
from dynaconf import Dynaconf
from granian import Granian
from granian.constants import Interfaces

from app.core.constants import PATH_TO_ENVS, PATH_TO_SECRETS, PATH_TO_SETTINGS
from app.schemas.logger import LoggerConfig
from app.schemas.server import ServerConfig


class ConfigContainer(containers.DeclarativeContainer):
    config = providers.Configuration()
    config.from_dict(
        Dynaconf(
            envvar_prefix=False,
            settings_file=[PATH_TO_SETTINGS, PATH_TO_SECRETS, PATH_TO_ENVS],
            environments=True,
            load_dotenv=False,
            merge_enabled=True,
        ).as_dict()
    )

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
        log_level=config.LOGGING.LEVEL,
        log_format=config.LOGGING.FORMAT,
    )


class ServerContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(
        packages=[
            "__main__",
        ]
    )
    config_container = providers.Container(ConfigContainer)

    granian_server = providers.Singleton(
        Granian,
        target=config_container.server_config.provided.target_run,  # Путь до вашего приложения (как строка)
        address=config_container.server_config.provided.host,  # Настройки сети
        port=config_container.server_config.provided.port,
        interface=Interfaces.ASGI,  # Явно указываем интерфейс (FastAPI - это ASGI)
        workers=config_container.server_config.provided.workers,  # Количество воркеров (для dev лучше 1)
        reload=config_container.server_config.provided.reload,  # Перезагрузка при изменении кода (для dev)
        factory=config_container.server_config.provided.factory,
        log_level=config_container.server_config.provided.log_level,
        log_access=config_container.server_config.provided.log_access,
    )


class AppContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(packages=["app"])
    config_container = providers.Container(ConfigContainer)
