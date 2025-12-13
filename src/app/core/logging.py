import logging.config

import structlog
from dependency_injector.wiring import Provide, inject

from app.core.containers import AppContainer
from app.schemas.logger import LoggerConfig


@inject
def setup_logging(
    logger_config: LoggerConfig = Provide[
        AppContainer.config_container.logger_config
    ],
) -> None:
    """
    Настраивает structlog + стандартный logging для JSON (Prod) или Console (Dev).
    """

    # 1. Общие процессоры (выполняются всегда)
    shared_processors = [
        structlog.contextvars.merge_contextvars,  # Добавляет контекст (request_id)
        structlog.stdlib.add_logger_name,  # Добавляет поле "logger": "app.services.user"
        structlog.stdlib.add_log_level,  # Добавляет поле "level": "info"
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),  # ISO8601 для ELK
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,  # Красивые трейсбеки
        structlog.processors.UnicodeDecoder(),
    ]

    # 2. Определяем режим (JSON или Текст)
    # Предполагаем, что в settings есть поле LOG_FORMAT="json" или "console"
    is_json_logs = logger_config.log_format == "json"
    log_level = logger_config.log_level

    if is_json_logs:
        # --- PROD: JSON ---
        shared_processors = [
            *shared_processors,
            # Превращает объект события в словарь для JSON
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.dict_tracebacks,  # Трейсбек как структурированный dict (для Kibana)
            structlog.processors.JSONRenderer(),
        ]
        # Для стандартного логгера нужен специальный форматтер
        formatter_class = structlog.stdlib.ProcessorFormatter
        formatter_kwargs = {
            "processor": structlog.processors.JSONRenderer(),
            "foreign_pre_chain": shared_processors,
        }
    else:
        # --- DEV: Console ---
        shared_processors = [
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(),  # Красивые цвета
        ]
        formatter_class = structlog.stdlib.ProcessorFormatter
        formatter_kwargs = {
            "processor": structlog.dev.ConsoleRenderer(),
            "foreign_pre_chain": shared_processors,
        }

    # 3. Конфигурация structlog
    shared_processors.append(
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter
    )
    structlog.configure(
        processors=shared_processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # 4. Конфигурация стандартного logging (чтобы перехватить Granian/Uvicorn)
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": formatter_class,  # Используем класс Structlog как форматтер
                **formatter_kwargs,
            },
        },
        "handlers": {
            "default": {
                "level": log_level,
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "": {  # Root logger (перехватывает всё)
                "handlers": ["default"],
                "level": log_level,
                "propagate": True,
            },
            "uvicorn.error": {
                "handlers": ["default"],
                "level": log_level,
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["default"],
                "level": log_level,
                "propagate": False,
            },
            "granian.access": {
                "handlers": ["default"],
                "level": log_level,
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(logging_config)
