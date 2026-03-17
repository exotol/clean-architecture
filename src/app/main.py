from __future__ import annotations

from typing import TYPE_CHECKING

from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject

from app.core.containers import ServerContainer
from app.infrastructure.observability.logging import setup_logging
from app.utils.configs import LoggerConfig
from app.utils.configs import OTLPConfig
from app.utils.configs import load_settings


if TYPE_CHECKING:
    from granian.server import MPServer
    from granian.server import MTServer


@inject
def main(
    granian_server: MPServer | MTServer = Provide[
        ServerContainer.granian_server
    ],
    logger_config: LoggerConfig = Provide[
        ServerContainer.infra_container.logger_config
    ],
    otlp_config: OTLPConfig = Provide[
        ServerContainer.infra_container.otlp_config
    ],
) -> None:
    """Configure logging and start the Granian server."""
    setup_logging(logger_config=logger_config, otlp_config=otlp_config)
    granian_server.serve()


def init_server_container() -> None:
    """Initialize DI container configuration for the server runtime."""
    container = ServerContainer()
    container.infra_container.config.from_dict(  # type: ignore[attr-defined]
        load_settings().as_dict(),
    )


if __name__ == "__main__":
    init_server_container()
    main()
