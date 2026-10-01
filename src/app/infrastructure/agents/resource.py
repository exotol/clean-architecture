from __future__ import annotations

import asyncio
from contextlib import ExitStack
import math
from typing import TYPE_CHECKING

from dependency_injector import resources
import httpx
from langchain_openai import ChatOpenAI

from app.core.exceptions import InfrastructureError
from app.domain.interfaces.agent_runner import IAgentRunner
from app.infrastructure.agents.langgraph_runner import AgentGateways
from app.infrastructure.agents.langgraph_runner import LangGraphAgentRunner
from app.infrastructure.gateways.agent_tools import DuckDuckGoSearchGateway
from app.infrastructure.gateways.agent_tools import (
    FrankfurterExchangeRateGateway,
)
from app.infrastructure.gateways.agent_tools import OpenMeteoGeocodingGateway
from app.infrastructure.gateways.agent_tools import OpenMeteoWeatherGateway


if TYPE_CHECKING:
    from app.domain.entities.agent import AgentAnswer
    from app.utils.agent_config import AgentConfig


class DisabledAgentRunner(IAgentRunner):
    """Keep the optional agent unavailable until explicitly configured."""

    async def run(self, query: str) -> AgentAnswer:
        """Report an unavailable agent without creating an LLM client."""
        _ = (self, query)
        message = "Agent is disabled. Configure AGENT.ENABLED and API_KEY."
        raise InfrastructureError(message, service_name="agent")


class AgentRunnerResource(resources.AsyncResource[IAgentRunner]):
    """Build the agent once per process and own its synchronous client."""

    async def init(
        self,
        config: AgentConfig,
        http_client: httpx.AsyncClient,
    ) -> IAgentRunner:
        """Compose adapters and graph from validated configuration."""
        self._stack = ExitStack()
        if not config.enabled:
            return DisabledAgentRunner()
        if not config.api_key.get_secret_value().strip():
            message = "AGENT.API_KEY is required when the agent is enabled"
            raise InfrastructureError(message, service_name="agent")

        with ExitStack() as stack:
            model = ChatOpenAI(
                model_name=config.model,
                openai_api_key=config.api_key,
                openai_api_base=config.base_url,
                request_timeout=config.model_timeout_seconds,
                max_retries=0,
                max_tokens=config.max_tokens,
                temperature=0,
                http_client=stack.enter_context(httpx.Client()),
                http_async_client=http_client,
                use_responses_api=False,
            )
            runner = LangGraphAgentRunner(
                model,
                _create_gateways(config, http_client),
                max_steps=config.max_steps,
                timeout_seconds=config.run_timeout_seconds,
            )
            self._stack = stack.pop_all()
            return runner

    async def shutdown(self, resource: IAgentRunner | None) -> None:
        """Close the owned client; the container owns the shared async one."""
        _ = resource
        await asyncio.to_thread(self._stack.close)


def _create_gateways(
    config: AgentConfig,
    client: httpx.AsyncClient,
) -> AgentGateways:
    """Compose the four tool ports with their external implementations."""
    return AgentGateways(
        geocoding=OpenMeteoGeocodingGateway(
            client,
            config.geocoding_url,
            timeout_seconds=config.tool_timeout_seconds,
        ),
        weather=OpenMeteoWeatherGateway(
            client,
            config.weather_url,
            timeout_seconds=config.tool_timeout_seconds,
        ),
        exchange_rate=FrankfurterExchangeRateGateway(
            client,
            config.currency_url,
            timeout_seconds=config.tool_timeout_seconds,
        ),
        web_search=DuckDuckGoSearchGateway(
            timeout_seconds=math.ceil(config.tool_timeout_seconds),
        ),
    )
