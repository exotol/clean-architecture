from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


if TYPE_CHECKING:
    from app.utils.configs import LoggerConfig
    from app.utils.configs import OTLPConfig


class LoggingEntity(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    logger_config: LoggerConfig
    otlp_config: OTLPConfig
    mock_tracer_provider: MagicMock = Field(default_factory=MagicMock)


class LoggingExpected(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    trace_provider_set: bool = True
    logger_removed: bool = True
    logger_configured: bool = True
