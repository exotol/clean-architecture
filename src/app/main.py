from dependency_injector.wiring import Provide, inject
from granian.server import MPServer, MTServer

from app.core.containers import ServerContainer


@inject
def main(
    granian_server: MPServer | MTServer = Provide[
        ServerContainer.granian_server
    ],
) -> None:
    granian_server.serve()


if __name__ == "__main__":
    container = ServerContainer()
    main()
