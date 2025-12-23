from enum import StrEnum

from dynaconf import Dynaconf
from pydantic import BaseModel

from app.core.constants import PATH_TO_ENVS, PATH_TO_SECRETS, PATH_TO_SETTINGS


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


class LoggerConfig(BaseModel):
    level: LogLevel
    format: str
    path: str | None
    rotation: str
    retention: str
    loggers_to_root: list[str]


class ServerConfig(BaseModel):
    host: str
    port: int
    workers: int
    reload: bool
    target_run: str
    factory: bool
    log_level: str
    log_access: bool
