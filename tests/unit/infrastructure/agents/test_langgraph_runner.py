from __future__ import annotations

import asyncio
from datetime import UTC
from datetime import date
from datetime import datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

import httpx
from langchain_core.language_models.fake_chat_models import (
    FakeMessagesListChatModel,
)
from langchain_core.messages import AIMessage
from langchain_core.messages import BaseMessage
from langchain_core.messages import HumanMessage
from openai import APIConnectionError
import pytest

from app.core.exceptions import InfrastructureError
from app.domain.entities.agent_tools import ExchangeRate
from app.domain.entities.agent_tools import Location
from app.domain.entities.agent_tools import SearchHit
from app.domain.entities.agent_tools import Weather
from app.domain.interfaces.agent_tools import IExchangeRateGateway
from app.domain.interfaces.agent_tools import IGeocodingGateway
from app.domain.interfaces.agent_tools import IWeatherGateway
from app.domain.interfaces.agent_tools import IWebSearchGateway
from app.infrastructure.agents import AgentGateways
from app.infrastructure.agents import LangGraphAgentRunner
from tests.schemas.unit.infrastructure.agent import AgentRunnerExpected


class ScriptedChatModel(FakeMessagesListChatModel):
    """Fake model that accepts tool binding for a real compiled graph."""

    def bind_tools(
        self,
        tools: Any,
        **kwargs: Any,
    ) -> ScriptedChatModel:
        """Accept the tools while retaining scripted responses."""
        del tools, kwargs
        return self


def create_gateways() -> tuple[AgentGateways, AsyncMock]:
    """Create isolated gateway doubles."""
    geocoding = AsyncMock(spec=IGeocodingGateway)
    weather = AsyncMock(spec=IWeatherGateway)
    exchange_rate = AsyncMock(spec=IExchangeRateGateway)
    web_search = AsyncMock(spec=IWebSearchGateway)
    web_search.search.return_value = ()
    return AgentGateways(
        geocoding,
        weather,
        exchange_rate,
        web_search,
    ), web_search


async def answer_with_last_query(messages: list[BaseMessage]) -> AIMessage:
    """Return the current invocation's user query."""
    query = next(
        message.content
        for message in reversed(messages)
        if isinstance(message, HumanMessage)
    )
    return AIMessage(content=f"answer:{query}")


@pytest.mark.anyio
async def test_runner_executes_all_tools_in_compiled_graph() -> None:
    # Arrange
    geocoding = AsyncMock(spec=IGeocodingGateway)
    weather = AsyncMock(spec=IWeatherGateway)
    exchange_rate = AsyncMock(spec=IExchangeRateGateway)
    web_search = AsyncMock(spec=IWebSearchGateway)
    geocoding.geocode.return_value = (
        Location("Moscow", "Russia", 55.75, 37.62, "Europe/Moscow"),
    )
    weather.weather.return_value = Weather(
        18.5,
        17.9,
        5.2,
        1,
        datetime(2026, 9, 8, 12, tzinfo=UTC),
        "Europe/Moscow",
    )
    exchange_rate.exchange_rate.return_value = ExchangeRate(
        "USD",
        "RUB",
        Decimal("81.25"),
        date(2026, 9, 8),
    )
    web_search.search.return_value = (
        SearchHit("Example", "https://example.com", "Untrusted snippet"),
    )
    model = ScriptedChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "geocode", "args": {"city": "Moscow"}, "id": "1"},
                    {
                        "name": "weather",
                        "args": {"latitude": 55.75, "longitude": 37.62},
                        "id": "2",
                    },
                    {
                        "name": "exchange_rate",
                        "args": {"base": "USD", "quote": "RUB"},
                        "id": "3",
                    },
                    {
                        "name": "web_search",
                        "args": {"query": "news"},
                        "id": "4",
                    },
                ],
            ),
            AIMessage(content="Moscow is warm; one USD is 81.25 RUB."),
        ],
    )
    runner = LangGraphAgentRunner(
        model,
        AgentGateways(geocoding, weather, exchange_rate, web_search),
        max_steps=5,
        timeout_seconds=2,
    )
    expected = AgentRunnerExpected(
        answer="Moscow is warm; one USD is 81.25 RUB.",
        tools_used=("geocode", "weather", "exchange_rate", "web_search"),
    )

    # Act
    actual = await runner.run("Tell me everything")

    # Assert
    assert actual.answer == expected.answer, (
        f"Expected answer {expected.answer}, got {actual.answer}"
    )
    assert actual.tools_used == expected.tools_used, (
        f"Expected tools {expected.tools_used}, got {actual.tools_used}"
    )
    assert geocoding.geocode.call_count == 1, (
        f"Expected one geocode call, got {geocoding.geocode.call_count}"
    )
    assert weather.weather.call_count == 1, (
        f"Expected one weather call, got {weather.weather.call_count}"
    )
    assert exchange_rate.exchange_rate.call_count == 1, (
        "Expected one exchange call, got "
        f"{exchange_rate.exchange_rate.call_count}"
    )
    assert web_search.search.call_count == 1, (
        f"Expected one search call, got {web_search.search.call_count}"
    )


@pytest.mark.anyio
async def test_runner_maps_step_limit_to_infrastructure_error() -> None:
    # Arrange
    gateways, web_search = create_gateways()
    repeated_call = AIMessage(
        content="",
        tool_calls=[
            {"name": "web_search", "args": {"query": "news"}, "id": "1"},
        ],
    )
    runner = LangGraphAgentRunner(
        ScriptedChatModel(responses=[repeated_call]),
        gateways,
        max_steps=2,
        timeout_seconds=2,
    )

    # Act
    with pytest.raises(InfrastructureError) as error_info:
        await runner.run("Keep searching")

    # Assert
    assert error_info.value.status_code == 503, (
        f"Expected status 503, got {error_info.value.status_code}"
    )
    assert web_search.search.call_count <= 1, (
        f"Expected at most one dispatch, got {web_search.search.call_count}"
    )


@pytest.mark.anyio
async def test_runner_maps_total_timeout_to_infrastructure_error() -> None:
    # Arrange
    gateways, _ = create_gateways()
    runner = LangGraphAgentRunner(
        ScriptedChatModel(
            responses=[AIMessage(content="late")],
            sleep=0.1,
        ),
        gateways,
        max_steps=3,
        timeout_seconds=0.001,
    )

    # Act
    with pytest.raises(InfrastructureError) as error_info:
        await runner.run("Wait")

    # Assert
    assert "timed out" in error_info.value.detail, (
        f"Expected timeout detail, got {error_info.value.detail}"
    )


@pytest.mark.anyio
async def test_runner_maps_openai_error_to_infrastructure_error() -> None:
    # Arrange
    gateways, _ = create_gateways()
    bound_model = MagicMock()
    bound_model.ainvoke = AsyncMock(
        side_effect=APIConnectionError(
            request=httpx.Request("POST", "https://llm"),
        ),
    )
    model = MagicMock()
    model.bind_tools.return_value = bound_model
    runner = LangGraphAgentRunner(
        model,
        gateways,
        max_steps=3,
        timeout_seconds=2,
    )

    # Act
    with pytest.raises(InfrastructureError) as error_info:
        await runner.run("Ask")

    # Assert
    assert error_info.value.status_code == 503, (
        f"Expected status 503, got {error_info.value.status_code}"
    )


@pytest.mark.anyio
async def test_runner_rejects_unknown_tool_before_dispatch() -> None:
    # Arrange
    gateways, web_search = create_gateways()
    model = ScriptedChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "fetch_url",
                        "args": {"url": "file:///etc/passwd"},
                        "id": "1",
                    },
                ],
            ),
        ],
    )
    runner = LangGraphAgentRunner(
        model,
        gateways,
        max_steps=3,
        timeout_seconds=2,
    )

    # Act
    with pytest.raises(InfrastructureError) as error_info:
        await runner.run("Read a file")

    # Assert
    assert "unknown tool" in error_info.value.detail, (
        f"Expected unknown-tool detail, got {error_info.value.detail}"
    )
    assert web_search.search.call_count == 0, (
        f"Expected no dispatcher call, got {web_search.search.call_count}"
    )


@pytest.mark.anyio
async def test_runner_keeps_concurrent_requests_isolated() -> None:
    # Arrange
    gateways, _ = create_gateways()
    bound_model = MagicMock()
    bound_model.ainvoke = AsyncMock(side_effect=answer_with_last_query)
    model = MagicMock()
    model.bind_tools.return_value = bound_model
    runner = LangGraphAgentRunner(
        model,
        gateways,
        max_steps=3,
        timeout_seconds=2,
    )

    # Act
    first, second = await asyncio.gather(
        runner.run("first"),
        runner.run("second"),
    )

    # Assert
    assert first.answer == "answer:first", (
        f"Expected isolated first answer, got {first.answer}"
    )
    assert second.answer == "answer:second", (
        f"Expected isolated second answer, got {second.answer}"
    )
    assert first.tools_used == second.tools_used == (), (
        "Expected no cross-request tool state, got "
        f"{first.tools_used} and {second.tools_used}"
    )
