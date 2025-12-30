from enum import StrEnum

from dynaconf import Dynaconf
from orendix import Component, Value, Configuration
from orendix.annotations import ConfigurationProperties
from pydantic import BaseModel

from app.core.constants import PATH_TO_ENVS
from app.core.constants import PATH_TO_SECRETS
from app.core.constants import PATH_TO_SETTINGS


def load_settings() -> Dynaconf:
    return Dynaconf(
        envvar_prefix=False,
        settings_file=[PATH_TO_SETTINGS, PATH_TO_SECRETS, PATH_TO_ENVS],
        environments=True,
        load_dotenv=False,
        merge_enabled=True,
    )


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    FATAL = "FATAL"
    NOTSET = "NOTSET"

@Component(name="logger_config")
class LoggerConfig(BaseModel):
    level: LogLevel = Value("${LOGGING.LEVEL}")
    format: str = Value("${LOGGING.FORMAT}")
    path: str | None = Value("${LOGGING.PATH:None}")
    rotation: str = Value("${LOGGING.ROTATION}")
    retention: str = Value("${LOGGING.RETENTION}")
    loggers_to_root: list[str] = Value("${LOGGING.LOGGERS_TO_ROOT}")


class MetricsConfig(BaseModel):
    duration_buckets: list[float]
    service_name: str


class ServerConfig(BaseModel):
    host: str
    port: int
    workers: int
    reload: bool
    target_run: str
    factory: bool
    log_level: str
    log_access: bool


class SecurityConfig(BaseModel):
    cors_origins: list[str]
    cors_allow_credentials: bool
    cors_allow_methods: list[str]
    cors_allow_headers: list[str]
    trusted_hosts: list[str]

@ConfigurationProperties(prefix="TRACING.OTLP")
@Component(name="otlp_config")
class OTLPConfig(BaseModel):
    enabled: bool
    endpoint: str
    service_name: str
    insecure: bool


class SerializationConfig(BaseModel):
    """Configuration for serializer behavior."""
    max_depth: int = 500
    warn_depth: int = 100
    max_objects: int = 100_000
    detect_cycles: bool = True
    fallback_on_error: bool = True
    use_orjson: bool = True


class ProfilingConfig(BaseModel):
    """Configuration for cProfile profiling."""
    enabled: bool = False
    output_dir: str = "profiles"
    sort_by: str = "cumulative"  # cumulative, time, calls
    top_n: int = 50