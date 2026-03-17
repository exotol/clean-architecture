from __future__ import annotations

from pydantic import BaseModel


class Healthcheck(BaseModel):
    """Ответ на запрос хелс-чека.

    Цель вернуть статус 200
    """
