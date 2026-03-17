from __future__ import annotations

from pydantic import BaseModel


class ProfilingDispatchEntity(BaseModel):
    """Input: profiling enabled or disabled."""

    enabled: bool


class ProfilingDispatchExpected(BaseModel):
    """Pass-through response and profiler call counts when enabled."""

    profiler_enable_calls: int
    profiler_disable_calls: int
