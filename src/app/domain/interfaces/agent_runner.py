from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from app.domain.entities.agent import AgentAnswer


class IAgentRunner(ABC):
    """Port for executing an agent conversation."""

    @abstractmethod
    async def run(self, query: str) -> AgentAnswer:
        """Run one isolated agent request."""
