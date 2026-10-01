from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from langchain_core.messages import BaseMessage


@dataclass(frozen=True, slots=True)
class AgentRunnerExpected:
    """Expected LangGraph runner result."""

    answer: str
    tools_used: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AgentGuardEntity:
    """Model response and execution limits for boundary checks."""

    response: BaseMessage
    max_steps: int = 3
    timeout_seconds: float = 2


@dataclass(frozen=True, slots=True)
class AgentGuardExpected:
    """Failure expected before an unsafe tool dispatch."""

    exception: type[Exception]
    message: str


@dataclass(frozen=True, slots=True)
class ToolFailureEntity:
    """Tool call and optional provider failure."""

    name: str
    arguments: dict[str, object]
    error: Exception | None = None


@dataclass(frozen=True, slots=True)
class ToolFailureExpected:
    """Whether the graph may recover from the tool failure."""

    recoverable: bool
