from __future__ import annotations

from pydantic import BaseModel


class MiddlewareListEntity(BaseModel):
    """Input: profiling and rate_limit config flags."""

    profiling_enabled: bool
    rate_limit_enabled: bool


class MiddlewareListExpected(BaseModel):
    """Expected middleware list length."""

    middleware_count: int
