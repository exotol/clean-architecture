from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.events import Events
from app.core.exceptions import BusinessError
from app.utils.monitor import monitor


if TYPE_CHECKING:
    from app.domain.entities.agent import AgentAnswer
    from app.domain.interfaces.agent_runner import IAgentRunner


class AgentService:
    """Application use case for answering a question through an agent."""

    def __init__(self, runner: IAgentRunner) -> None:
        self._runner = runner

    @monitor(
        event_name=Events.AGENT_SERVICE,
        use_log_args=False,
        use_log_result=False,
    )
    async def answer(self, query: str) -> AgentAnswer:
        """Validate and pass a user question to the configured agent."""
        if not query.strip():
            raise BusinessError("Agent query must not be blank")
        return await self._runner.run(query=query)
