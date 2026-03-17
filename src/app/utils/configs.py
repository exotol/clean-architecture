from __future__ import annotations

from enum import StrEnum
from typing import Literal

from dynaconf import Dynaconf
from pydantic import BaseModel

from app.core.constants import PATH_TO_ENVS
from app.core.constants import PATH_TO_SECRETS
from app.core.constants import PATH_TO_SETTINGS


def load_settings() -> Dynaconf:
    """Load application settings via Dynaconf."""
    return Dynaconf(
        envvar_prefix=False,
        settings_file=[PATH_TO_SETTINGS, PATH_TO_SECRETS, PATH_TO_ENVS],
        environments=True,
        load_dotenv=False,
        merge_enabled=True,
    )


class LogLevel(StrEnum):
    """Supported logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    FATAL = "FATAL"
    NOTSET = "NOTSET"


class LoggerConfig(BaseModel):
    """Logging configuration."""

    level: LogLevel
    format: str
    path: str | None
    rotation: str
    retention: str
    loggers_to_root: list[str]
    # "json" for prod; "text" for local dev (ConsoleRenderer colors)
    log_format: Literal["json", "text"] = "json"
    # Logger names to mute (NullHandler), e.g. ["httpx", "httpcore"]
    mute_loggers: list[str] = []


class MetricsConfig(BaseModel):
    """Metrics configuration."""

    duration_buckets: list[float]
    service_name: str


class ServerConfig(BaseModel):
    """Server configuration."""

    host: str
    port: int
    workers: int
    reload: bool
    target_run: str
    factory: bool
    log_level: str
    log_access: bool


class SecurityConfig(BaseModel):
    """Security-related configuration (CORS, trusted hosts)."""

    cors_origins: list[str]
    cors_allow_credentials: bool
    cors_allow_methods: list[str]
    cors_allow_headers: list[str]
    trusted_hosts: list[str]


class OTLPConfig(BaseModel):
    """OpenTelemetry OTLP exporter configuration."""

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


class RateLimitConfig(BaseModel):
    """Configuration for rate limiting (in-memory)."""

    enabled: bool = False
    requests_per_window: int = 100
    window_seconds: float = 60.0
    key_header: str | None = None  # header value, or client IP if None


class CacheConfig(BaseModel):
    """Configuration for in-memory cache."""

    enabled: bool = False
    ttl_seconds: int = 300
    max_size: int = 10_000


class CircuitBreakerConfig(BaseModel):
    """Configuration for circuit breaker on external calls."""

    enabled: bool = False
    failure_threshold: int = 5
    recovery_timeout_seconds: float = 30.0


class HttpClientConfig(BaseModel):
    """Configuration for HTTP clients (httpx). Transport and timeouts."""

    base_url: str = "http://localhost"
    timeout_seconds: float = 30.0
    max_connections: int = 100
    max_keepalive_connections: int = 20
    keepalive_expiry_seconds: float = 5.0


def get_http_client_config(
    settings: Dynaconf | None = None,
) -> HttpClientConfig:
    """Return HttpClientConfig from Dynaconf; uses load_settings() if None."""
    if settings is None:
        settings = load_settings()
    return HttpClientConfig(
        base_url=settings.HTTP_CLIENT.BASE_URL,
        timeout_seconds=float(settings.HTTP_CLIENT.TIMEOUT_SECONDS),
        max_connections=int(settings.HTTP_CLIENT.MAX_CONNECTIONS),
        max_keepalive_connections=int(
            settings.HTTP_CLIENT.MAX_KEEPALIVE_CONNECTIONS,
        ),
        keepalive_expiry_seconds=float(
            settings.HTTP_CLIENT.KEEPALIVE_EXPIRY_SECONDS,
        ),
    )
