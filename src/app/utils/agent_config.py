from __future__ import annotations

from pydantic import BaseModel
from pydantic import Field
from pydantic import SecretStr


class AgentConfig(BaseModel):
    """Validated configuration of the optional ReAct agent."""

    enabled: bool = Field(..., description="Включить агента")
    api_key: SecretStr = Field(..., description="Ключ API модели")
    model: str = Field(..., min_length=1, description="Имя модели с tools")
    base_url: str = Field(..., description="Базовый URL API модели")
    model_timeout_seconds: float = Field(
        ...,
        gt=0,
        description="Таймаут одного обращения к модели",
    )
    run_timeout_seconds: float = Field(
        ...,
        gt=0,
        description="Общий таймаут выполнения графа",
    )
    max_steps: int = Field(
        ...,
        ge=2,
        le=100,
        description="Лимит supersteps графа",
    )
    max_tokens: int = Field(
        ...,
        ge=1,
        le=16384,
        description="Максимум токенов ответа модели",
    )
    tool_timeout_seconds: float = Field(
        ...,
        gt=0,
        description="Таймаут HTTP инструментов и поиска",
    )
    geocoding_url: str = Field(..., description="URL Open-Meteo Geocoding")
    weather_url: str = Field(..., description="URL Open-Meteo Forecast")
    currency_url: str = Field(..., description="URL Frankfurter v2")
