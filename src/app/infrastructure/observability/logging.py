from __future__ import annotations

import logging
import sys
from typing import Any
from typing import TYPE_CHECKING

from dependency_injector.wiring import Provide
from dependency_injector.wiring import inject
from loguru import logger
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import \
    OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.export import ConsoleSpanExporter

from app.core.containers import AppContainer

if TYPE_CHECKING:
    from types import FrameType

    from app.utils.configs import LoggerConfig
    from app.utils.configs import OTLPConfig


class InterceptHandler(logging.Handler):
    """
    Перехватывает стандартные логи Python и отправляет их в Loguru.

    https://github.com/Delgan/loguru
    """

    def __init__(self, depth: int = 2) -> None:
        super().__init__()
        self._depth = depth

    def emit(self, record: logging.LogRecord) -> None:
        # Получаем соответствующий уровень логов Loguru
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Ищем, откуда был вызов
        frame: FrameType | None = logging.currentframe()
        depth = self._depth
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def record_patcher(record: dict[str, Any]) -> None:
    """
    Патчер для Loguru, который добавляет trace_id и span_id из OpenTelemetry.

    Args:
        record: Словарь с записью лога.
    """
    span = trace.get_current_span()
    if not span:
        return

    span_context = span.get_span_context()
    if span_context.is_valid:
        record["extra"]["trace_id"] = format(span_context.trace_id, "032x")
        record["extra"]["span_id"] = format(span_context.span_id, "016x")


@inject
def setup_logging(
    logger_config: LoggerConfig = Provide[
        AppContainer.infra_container.logger_config
    ],
    otlp_config: OTLPConfig = Provide[
        AppContainer.infra_container.otlp_config
    ],
) -> None:
    # 0. Настраиваем OpenTelemetry
    resource = Resource.create(
        attributes={"service.name": otlp_config.service_name}
    )
    provider = TracerProvider(resource=resource)

    # Выбираем экспортер
    if otlp_config.enabled:
        if otlp_config.endpoint == OTLP_LOCAL_ENDPOINT:
            processor = BatchSpanProcessor(ConsoleSpanExporter())
        else:
            processor = BatchSpanProcessor(
                OTLPSpanExporter(
                    endpoint=otlp_config.endpoint,
                    insecure=otlp_config.insecure,
                )
            )
        provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)

    # 1. Удаляем дефолтный обработчик Loguru
    logger.remove()

    # 2. Добавляем патчер для trace_id
    logger.configure(patcher=record_patcher)

    # 3. Добавляем вывод в консоль (stdout)
    logger.add(
        sys.stdout,
        format=logger_config.format,
        level=logger_config.level,
    )

    if logger_config.path:
        logger.add(
            logger_config.path,
            rotation=logger_config.rotation,
            retention=logger_config.retention,
            compression="zip",
            level=logger_config.level,
            serialize=True,
            enqueue=True,
            backtrace=True,
            diagnose=True,
        )

    # 5. Перехват стандартных логгеров (Uvicorn, FastAPI, Granian)
    logging.basicConfig(handlers=[InterceptHandler()], level=0)

    # Список библиотек, чьи логи мы хотим видеть в нашем формате
    loggers = logger_config.loggers_to_root

    for logger_name in loggers:
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
        logging_logger.propagate = False
