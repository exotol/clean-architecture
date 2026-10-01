from __future__ import annotations

from unittest.mock import AsyncMock

from dependency_injector import providers
import pytest

from app.application.services.agent_service import AgentService
from app.core.exceptions import BusinessError
from app.core.exceptions import InfrastructureError
from app.domain.entities.agent import AgentAnswer
from app.infrastructure.agents.resource import DisabledAgentRunner
from tests.schemas.e2e.api.agent import AgentFailureEntity
from tests.schemas.e2e.api.agent import AgentFailureExpected


@pytest.mark.anyio
async def test_agent_http_contract_and_correlation(client, app) -> None:
    # Arrange
    service = AsyncMock(spec=AgentService)
    service.answer.return_value = AgentAnswer(
        answer="Answer with sources",
        tools_used=("geocode", "weather", "exchange_rate", "web_search"),
    )
    with app.state.container.agent_service.override(providers.Object(service)):
        # Act
        response = await client.post(
            "/v1/agent/answer",
            headers={"X-Request-ID": "habr-agent-success"},
            json={"query": "Weather and exchange rate in Berlin"},
        )

    # Assert
    assert response.status_code == 200, (
        f"Expected 200, got {response.status_code}: {response.text}"
    )
    assert response.json() == {
        "answer": "Answer with sources",
        "tools_used": ["geocode", "weather", "exchange_rate", "web_search"],
    }, f"Unexpected response contract: {response.json()}"
    assert response.headers["X-Request-ID"] == "habr-agent-success", (
        f"Unexpected correlation header: {response.headers}"
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            AgentFailureEntity(BusinessError("Question needs clarification")),
            AgentFailureExpected(400, "BUSINESS_RULE_VIOLATION"),
            id="business_rule",
        ),
        pytest.param(
            AgentFailureEntity(InfrastructureError("Model unavailable")),
            AgentFailureExpected(503, "INFRASTRUCTURE_ERROR"),
            id="model_unavailable",
        ),
    ],
)
async def test_agent_http_error_mapping(client, app, entity, expected) -> None:
    # Arrange
    service = AsyncMock(spec=AgentService)
    service.answer.side_effect = entity.exception
    with app.state.container.agent_service.override(providers.Object(service)):
        # Act
        response = await client.post(
            "/v1/agent/answer",
            headers={"X-Request-ID": "habr-agent-error"},
            json={"query": "Weather in Berlin"},
        )

    # Assert
    assert response.status_code == expected.status_code, (
        f"Expected {expected.status_code}, got {response.status_code}"
    )
    body = response.json()
    assert body["reason"] == expected.reason, (
        f"Expected {expected.reason}, got {body}"
    )
    assert body["trace_id"] == "habr-agent-error", (
        f"Expected preserved correlation ID, got {body}"
    )
    assert body["instance"] == "/v1/agent/answer", (
        f"Unexpected error instance: {body}"
    )


@pytest.mark.anyio
async def test_disabled_agent_uses_existing_problem_details(
    client,
    app,
) -> None:
    # Arrange
    service = AgentService(DisabledAgentRunner())
    with app.state.container.agent_service.override(providers.Object(service)):
        # Act
        response = await client.post(
            "/v1/agent/answer",
            headers={"X-Request-ID": "habr-disabled"},
            json={"query": "Weather in Berlin"},
        )

    # Assert
    assert response.status_code == 503, (
        f"Expected disabled agent 503, got {response.status_code}"
    )
    assert response.json()["reason"] == "INFRASTRUCTURE_ERROR", (
        f"Unexpected disabled agent contract: {response.json()}"
    )
    assert response.headers["Retry-After"] == "30", (
        f"Expected existing 503 retry policy, got {response.headers}"
    )
