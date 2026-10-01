from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field


@dataclass(frozen=True, slots=True)
class AgentAnswer:
    """Result produced by the conversational agent.

    Attributes:
        answer: Final user-facing answer without hidden model reasoning.
        tools_used: Ordered unique names of tools used for the answer.
    """

    answer: str = field(
        metadata={"description": "Final user-facing agent answer"},
    )
    tools_used: tuple[str, ...] = field(
        metadata={"description": "Ordered unique names of invoked tools"},
    )
