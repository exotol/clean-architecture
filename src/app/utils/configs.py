from __future__ import annotations

from enum import StrEnum
from typing import Literal

from dynaconf import Dynaconf
from pydantic import BaseModel
from pydantic import Field

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

    level: LogLevel = Field(..., description="Уровень логирования")
    format: str = Field(..., description="Шаблон формата логов")
    path: str | None = Field(..., description="Путь к файлу логов")
    rotation: str = Field(..., description="Правило ротации логов")
    retention: str = Field(..., description="Срок хранения ротированных логов")
    loggers_to_root: list[str] = Field(
        ...,
        description="Список логгеров для перенаправления в root",
    )
    # "json" for prod; "text" for local dev (ConsoleRenderer colors)
    log_format: Literal["json", "text"] = Field(
        "json",
        description="Формат вывода логов: json или text",
    )
    # Logger names to mute (NullHandler), e.g. ["httpx", "httpcore"]
    mute_loggers: list[str] = Field(
        default=[],
        description="Список приглушаемых логгеров",
    )


class MetricsConfig(BaseModel):
    """Metrics configuration."""

    duration_buckets: list[float] = Field(
        ...,
        description="Границы корзин гистограммы длительности",
    )
    service_name: str = Field(
        ...,
        description="Имя сервиса для экспорта метрик",
    )


class ServerConfig(BaseModel):
    """Server configuration."""

    host: str = Field(..., description="Хост для запуска сервера")
    port: int = Field(..., description="Порт сервера")
    workers: int = Field(..., description="Количество рабочих процессов")
    reload: bool = Field(
        ...,
        description="Флаг автоперезагрузки при изменении кода",
    )
    target_run: str = Field(..., description="Целевая точка входа для запуска")
    factory: bool = Field(
        ...,
        description="Использовать ли фабрику приложений",
    )
    log_level: str = Field(..., description="Уровень логирования сервера")
    log_access: bool = Field(
        ...,
        description="Включить ли логирование HTTP запросов",
    )


class SecurityConfig(BaseModel):
    """Security-related configuration (CORS, trusted hosts)."""

    cors_origins: list[str] = Field(
        ...,
        description="Разрешенные CORS origins",
    )
    cors_allow_credentials: bool = Field(
        ...,
        description="Разрешить передачу credentials в CORS",
    )
    cors_allow_methods: list[str] = Field(
        ...,
        description="Разрешенные HTTP методы CORS",
    )
    cors_allow_headers: list[str] = Field(
        ...,
        description="Разрешенные заголовки CORS",
    )
    trusted_hosts: list[str] = Field(
        ...,
        description="Список доверенных хостов",
    )


class OTLPConfig(BaseModel):
    """OpenTelemetry OTLP exporter configuration."""

    enabled: bool = Field(..., description="Флаг активности OTLP экспортера")
    endpoint: str = Field(..., description="Эндпоинт OTLP коллектора")
    service_name: str = Field(..., description="Имя сервиса в трейсах OTLP")
    insecure: bool = Field(
        ...,
        description="Использовать ли небезопасное соединение",
    )


class SerializationConfig(BaseModel):
    """Configuration for serializer behavior."""

    max_depth: int = Field(
        500,
        description="Максимальная глубина сериализации",
    )
    warn_depth: int = Field(
        100,
        description="Глубина сериализации для предупреждения",
    )
    max_objects: int = Field(
        100_000,
        description="Максимальное количество сериализуемых объектов",
    )
    detect_cycles: bool = Field(
        default=True,
        description="Флаг обнаружения циклических ссылок",
    )
    fallback_on_error: bool = Field(
        default=True,
        description="Использовать fallback при ошибке сериализации",
    )
    use_orjson: bool = Field(
        default=True,
        description="Использовать ли быстрый движок orjson",
    )


class ProfilingConfig(BaseModel):
    """Configuration for cProfile profiling."""

    enabled: bool = Field(
        default=False,
        description="Флаг включения профилирования",
    )
    output_dir: str = Field(
        "profiles",
        description="Директория сохранения профилей",
    )
    sort_by: str = Field(
        "cumulative",
        description="Критерий сортировки статистики профилирования",
    )
    top_n: int = Field(
        50,
        description="Количество верхних строк отчета профилирования",
    )


class RateLimitConfig(BaseModel):
    """Configuration for rate limiting (in-memory)."""

    enabled: bool = Field(
        default=False,
        description="Флаг включения ограничения частоты запросов",
    )
    requests_per_window: int = Field(
        100,
        description="Лимит запросов за окно времени",
    )
    window_seconds: float = Field(
        60.0,
        description="Длительность окна ограничения в секундах",
    )
    key_header: str | None = Field(
        None,
        description="Заголовок для ключа лимитера (или IP клиента)",
    )


class CacheConfig(BaseModel):
    """Configuration for in-memory cache."""

    enabled: bool = Field(
        default=False,
        description="Флаг включения кэширования",
    )
    ttl_seconds: int = Field(
        300,
        description="Время жизни записи в кэше в секундах",
    )
    max_size: int = Field(
        10_000,
        description="Максимальное количество записей в кэше",
    )


class CircuitBreakerConfig(BaseModel):
    """Configuration for circuit breaker on external calls."""

    enabled: bool = Field(
        default=False,
        description="Флаг включения circuit breaker",
    )
    failure_threshold: int = Field(
        5,
        description="Порог количества ошибок для размыкания цепи",
    )
    recovery_timeout_seconds: float = Field(
        30.0,
        description="Время ожидания восстановления в секундах",
    )


class HttpClientConfig(BaseModel):
    """Configuration for HTTP clients (httpx). Transport and timeouts."""

    base_url: str = Field(
        "http://localhost",
        description="Базовый URL HTTP клиента",
    )
    timeout_seconds: float = Field(
        30.0,
        description="Таймаут запросов в секундах",
    )
    max_connections: int = Field(
        100,
        description="Максимальное количество соединений в пуле",
    )
    max_keepalive_connections: int = Field(
        20,
        description="Максимальное количество keep-alive соединений",
    )
    keepalive_expiry_seconds: float = Field(
        5.0,
        description="Время жизни keep-alive соединения в секундах",
    )


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
