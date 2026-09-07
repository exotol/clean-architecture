from __future__ import annotations

from pydantic import BaseModel
from pydantic import Field


class Healthcheck(BaseModel):
    """Ответ на запрос хелс-чека.

    Цель вернуть статус 200
    """


class Liveness(BaseModel):
    """Liveness probe response (process is running)."""

    status: str = Field("ok", description="Статус работоспособности сервиса")


class Readiness(BaseModel):
    """Readiness probe response (ready to accept traffic)."""

    status: str = Field(
        "ok",
        description="Статус готовности сервиса принимать трафик",
    )
