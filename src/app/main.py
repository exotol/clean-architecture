from dependency_injector.wiring import Provide, inject
from granian.server import MPServer, MTServer

from app.core.containers import ServerContainer
from app.infrastructure.observability.logging import setup_logging
from app.utils.configs import LoggerConfig, load_settings


@inject
def main(
    granian_server: MPServer | MTServer = Provide[
        ServerContainer.granian_server
    ],
    logger_config: LoggerConfig = Provide[
        ServerContainer.infra_container.logger_config
    ],
) -> None:
    setup_logging(logger_config=logger_config)
    granian_server.serve()


def init_server_container() -> None:
    settings_dict = load_settings().as_dict()
    container = ServerContainer()
    container.infra_container.config.from_dict(settings_dict)


if __name__ == "__main__":
    init_server_container()
    main()
