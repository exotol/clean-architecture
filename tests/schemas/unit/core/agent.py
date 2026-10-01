from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AgentConfigEntity:
    """Input to agent resource setup."""

    enabled: bool
    api_key: str


@dataclass(frozen=True, slots=True)
class AgentConfigExpected:
    """Expected availability of an agent resource."""

    fails_during_init: bool


@dataclass(frozen=True, slots=True)
class AgentPayloadEntity:
    """API request submitted to the agent."""

    payload: dict[str, object]


@dataclass(frozen=True, slots=True)
class AgentPayloadExpected:
    """Expected API validation status."""

    status_code: int
