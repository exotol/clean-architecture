from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AgentFailureEntity:
    """Failure raised by the application boundary."""

    exception: Exception


@dataclass(frozen=True, slots=True)
class AgentFailureExpected:
    """Expected public error contract."""

    status_code: int
    reason: str
