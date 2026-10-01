from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from app.domain.entities.agent import AgentAnswer


@dataclass(frozen=True, slots=True)
class AgentServiceEntity:
    """Input for an agent service scenario."""

    query: str
    runner_result: AgentAnswer | None = None


@dataclass(frozen=True, slots=True)
class AgentServiceExpected:
    """Expected agent service outcome."""

    result: AgentAnswer | None = None
    exception: type[Exception] | None = None
