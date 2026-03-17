from __future__ import annotations

from pydantic import BaseModel


class ReadinessProbeEntity(BaseModel):
    """Input: checker.is_ready return value."""

    is_ready: bool


class ReadinessProbeExpected(BaseModel):
    """Expected result of readiness() call."""

    # True -> result == Readiness(); False -> JSONResponse
    returns_readiness_schema: bool
    status_code: int | None  # When JSONResponse
    body_status_value: str | None  # When JSONResponse: body["status"]
