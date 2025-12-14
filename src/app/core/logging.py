from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

from dependency_injector.wiring import Provide, inject
from loguru import logger

from app.core.containers import AppContainer

if TYPE_CHECKING:
    from types import FrameType

    from app.schemas.logger import LoggerConfig


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


@inject
def setup_logging(
    logger_config: LoggerConfig = Provide[
        AppContainer.config_container.logger_config
    ],
) -> None:
    # 1. Удаляем дефолтный обработчик Loguru
    logger.remove()

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
