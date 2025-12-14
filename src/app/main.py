from dependency_injector.wiring import Provide, inject
from granian.server import MPServer, MTServer

from app.core.config import load_settings
from app.core.containers import ServerContainer
from app.core.logging import setup_logging
from app.schemas.logger import LoggerConfig


@inject
def main(
    granian_server: MPServer | MTServer = Provide[
        ServerContainer.granian_server
    ],
    logger_config: LoggerConfig = Provide[
        ServerContainer.config_container.logger_config
    ],
) -> None:
    setup_logging(logger_config=logger_config)
    granian_server.serve()


def init_server_container() -> None:
    settings_dict = load_settings().as_dict()
    container = ServerContainer()
    container.config_container.config.from_dict(settings_dict)


if __name__ == "__main__":
    init_server_container()
    main()
