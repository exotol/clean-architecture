from dependency_injector import containers
from dependency_injector import providers
from granian import Granian
from granian.constants import Interfaces

from app.application.services.search_service import SearchService
from app.infrastructure.observability.strategies.logging import StandardLoggingStrategy
from app.infrastructure.observability.strategies.metrics import OpentelemetryMetricsStrategy
from app.infrastructure.observability.strategies.tracing import OpentelemetryTracingStrategy
from app.infrastructure.persistence.repositories.search_repository import (
    SearchRepository,
)
from app.utils.configs import LoggerConfig
from app.utils.configs import MetricsConfig
from app.utils.configs import OTLPConfig
from app.utils.configs import ProfilingConfig
from app.utils.configs import SecurityConfig
from app.utils.configs import SerializationConfig
from app.utils.configs import ServerConfig
from app.utils.serializer import ItemSerializer


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

    # logger_config = providers.Singleton(
    #     LoggerConfig,
    #     level=config.LOGGING.LEVEL,
    #     format=config.LOGGING.FORMAT,
    #     path=config.LOGGING.PATH,
    #     rotation=config.LOGGING.ROTATION,
    #     retention=config.LOGGING.RETENTION,
    #     loggers_to_root=config.LOGGING.LOGGERS_TO_ROOT,
    # )

    metrics_config = providers.Singleton(
        MetricsConfig,
        duration_buckets=config.METRICS.DURATION.BUCKETS,
        service_name=config.METRICS.SERVICE_NAME
    )

    security_config = providers.Singleton(
        SecurityConfig,
        cors_origins=config.SECURITY.CORS.ORIGINS,
        cors_allow_credentials=config.SECURITY.CORS.ALLOW.CREDENTIALS,
        cors_allow_methods=config.SECURITY.CORS.ALLOW.METHODS,
        cors_allow_headers=config.SECURITY.CORS.ALLOW.HEADERS,
        trusted_hosts=config.SECURITY.TRUSTED.HOSTS
    )
    #
    # otlp_config = providers.Singleton(
    #     OTLPConfig,
    #     enabled=config.TRACING.OTLP.ENABLED,
    #     endpoint=config.TRACING.OTLP.ENDPOINT,
    #     service_name=config.TRACING.OTLP.SERVICE_NAME,
    #     insecure=config.TRACING.OTLP.INSECURE
    # )

    serialization_config = providers.Singleton(
        SerializationConfig,
        max_depth=config.SERIALIZATION.MAX_DEPTH.as_int(),
        warn_depth=config.SERIALIZATION.WARN_DEPTH.as_int(),
        max_objects=config.SERIALIZATION.MAX_OBJECTS.as_int(),
        detect_cycles=config.SERIALIZATION.DETECT_CYCLES,
        fallback_on_error=config.SERIALIZATION.FALLBACK_ON_ERROR,
        use_orjson=config.SERIALIZATION.USE_ORJSON,
    )

    serializer = providers.Singleton(
        ItemSerializer,
        config=serialization_config,
    )

    profiling_config = providers.Singleton(
        ProfilingConfig,
        enabled=config.PROFILING.ENABLED,
        output_dir=config.PROFILING.OUTPUT_DIR,
        sort_by=config.PROFILING.SORT_BY,
        top_n=config.PROFILING.TOP_N.as_int(),
    )

    logging_strategy = providers.Singleton(
        StandardLoggingStrategy,
        serializer=serializer,
    )
    tracing_strategy = providers.Singleton(OpentelemetryTracingStrategy)
    metrics_strategy = providers.Singleton(OpentelemetryMetricsStrategy)


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
