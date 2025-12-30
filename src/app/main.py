from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from granian.server import MPServer
from granian.server import MTServer
from orendix import Configuration, Autowired, Bean, Qualifier, Container
from loguru import logger
from app.core.containers import ServerContainer
from app.infrastructure.observability.logging import setup_logging
from app.utils.configs import LoggerConfig, ServerConfig
from app.utils.configs import OTLPConfig
from app.utils.configs import load_settings
from granian import Granian


@Configuration
class AppConfig:

    @Bean(name="granian_server")
    def create_server(self, server_config: ServerConfig) -> MPServer | MTServer:
        logger.info(f"{server_config.model_dump(by_alias=True)}")
        return Granian(**server_config.model_dump(by_alias=True))


@Autowired(required=True)
def main(
    granian_server: MPServer | MTServer = Qualifier("granian_server")
) -> None:
    setup_logging()
    granian_server.serve()


def init_server_container() -> None:
    o_container = Container()
    o_container.use_dynaconf(load_settings())

    container = ServerContainer()
    container.infra_container.config.from_dict(load_settings().as_dict())


if __name__ == "__main__":
    init_server_container()
    main()
