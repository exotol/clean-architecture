from __future__ import annotations

from pydantic import BaseModel


class MiddlewareListEntity(BaseModel):
    """Input: profiling and rate_limit config flags."""

    profiling_enabled: bool
    rate_limit_enabled: bool


class MiddlewareListExpected(BaseModel):
    """Expected middleware list length."""

    middleware_count: int


class LifespanFailureEntity(BaseModel):
    """Input selecting a synchronous or asynchronous initialization failure."""

    asynchronous: bool


class LifespanFailureExpected(BaseModel):
    """Expected cleanup calls after initialization failure."""

    shutdown_calls: int
    unwire_calls: int
