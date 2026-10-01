from __future__ import annotations

from datetime import UTC
from datetime import date
from datetime import datetime
from decimal import Decimal
import json
from typing import Any
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage
from langchain_core.messages import ToolMessage
import pytest

from app.domain.entities.agent_tools import ExchangeRate
from app.domain.entities.agent_tools import Location
from app.domain.entities.agent_tools import SearchHit
from app.domain.entities.agent_tools import Weather
from app.infrastructure.agents import LangGraphAgentRunner
from tests.unit.infrastructure.agents.test_langgraph_runner import (
    create_gateways,
)


class ObservationPlanner:
    """Choose the next action from actual tool observations in the graph."""

    def __init__(self) -> None:
        self.observations: dict[str, Any] = {}
        self.turns = 0

    async def choose(self, messages) -> AIMessage:
        self.turns += 1
        self.observations = {
            message.name: json.loads(message.content)
            for message in messages
            if isinstance(message, ToolMessage)
        }
        if "geocode" not in self.observations:
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "geocode",
                        "args": {"city": "Berlin"},
                        "id": "geo",
                    },
                    {
                        "name": "exchange_rate",
                        "args": {"base": "EUR", "quote": "USD"},
                        "id": "fx",
                    },
                    {
                        "name": "web_search",
                        "args": {"query": "Berlin official tourism"},
                        "id": "web",
                    },
                ],
            )
        if "weather" not in self.observations:
            location = self.observations["geocode"][0]
            return AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "weather",
                        "args": {
                            "latitude": location["latitude"],
                            "longitude": location["longitude"],
                        },
                        "id": "weather",
                    },
                ],
            )
        weather = self.observations["weather"]
        rate = self.observations["exchange_rate"]
        hit = self.observations["web_search"][0]
        return AIMessage(
            content=(
                f"{weather['temperature_c']} C at {weather['observed_at']}; "
                f"EUR/USD {rate['rate']} on {rate['date']}; {hit['url']}"
            ),
        )


@pytest.mark.anyio
async def test_observations_drive_a_dependent_weather_tool_call() -> None:
    # Arrange
    gateways, search = create_gateways()
    gateways.geocoding.geocode.return_value = (
        Location("Berlin", "Germany", 52.52437, 13.41053, "Europe/Berlin"),
    )
    gateways.weather.weather.return_value = Weather(
        21.5,
        20.0,
        5.0,
        1,
        datetime(2026, 9, 8, 10, tzinfo=UTC),
        "UTC",
    )
    gateways.exchange_rate.exchange_rate.return_value = ExchangeRate(
        "EUR",
        "USD",
        Decimal("1.162500000000000001"),
        date(2026, 9, 8),
    )
    search.search.return_value = (
        SearchHit("Tourism", "https://www.visitberlin.de/en", "Visitor guide"),
    )
    planner = ObservationPlanner()
    bound_model = MagicMock()
    bound_model.ainvoke = AsyncMock(side_effect=planner.choose)
    model = MagicMock()
    model.bind_tools.return_value = bound_model
    runner = LangGraphAgentRunner(
        model,
        gateways,
        max_steps=7,
        timeout_seconds=2,
    )

    # Act
    answer = await runner.run("Weather, exchange rate and travel sources")

    # Assert
    assert gateways.weather.weather.call_args.args == (52.52437, 13.41053), (
        "Weather coordinates must originate in the geocoding observation"
    )
    assert planner.turns == 3, (
        f"Expected three model turns, got {planner.turns}"
    )
    assert answer.answer == (
        "21.5 C at 2026-09-08T10:00:00+00:00; "
        "EUR/USD 1.162500000000000001 on 2026-09-08; "
        "https://www.visitberlin.de/en"
    ), f"Final answer must use actual tool payloads: {answer.answer}"
    assert answer.tools_used == (
        "geocode",
        "exchange_rate",
        "web_search",
        "weather",
    ), f"Unexpected observation order: {answer.tools_used}"
    assert planner.observations["geocode"][0]["source"] == (
        "https://geocoding-api.open-meteo.com"
    ), f"Missing geocoding source: {planner.observations}"
    assert planner.observations["weather"]["source"] == (
        "https://api.open-meteo.com"
    ), f"Missing weather source: {planner.observations}"
    assert planner.observations["exchange_rate"]["source"] == (
        "https://frankfurter.dev"
    ), f"Missing exchange-rate source: {planner.observations}"
