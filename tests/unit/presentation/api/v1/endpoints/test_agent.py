from __future__ import annotations

from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.application.services.agent_service import AgentService
from app.domain.entities.agent import AgentAnswer
from app.presentation.api.schemas.agent import AgentRequest
from app.presentation.api.v1.endpoints.agent import create_agent_router
from app.presentation.api.v1.endpoints.agent import generate_agent_answer
from tests.schemas.unit.core.agent import AgentPayloadEntity
from tests.schemas.unit.core.agent import AgentPayloadExpected


@pytest.mark.anyio
async def test_generate_agent_answer_maps_domain_result() -> None:
    # Arrange
    service = AsyncMock(spec=AgentService)
    service.answer.return_value = AgentAnswer(
        answer="See the cited source",
        tools_used=("web_search",),
    )
    request = AgentRequest(query="Find the official documentation")

    # Act
    response = await generate_agent_answer(request, agent_service=service)

    # Assert
    assert response.answer == "See the cited source", (
        f"Unexpected mapped answer: {response.answer}"
    )
    assert response.tools_used == ["web_search"], (
        f"Unexpected mapped tools: {response.tools_used}"
    )
    assert service.answer.call_args.args == (request.query,), (
        f"Unexpected use-case arguments: {service.answer.call_args}"
    )


@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            AgentPayloadEntity({}),
            AgentPayloadExpected(422),
            id="missing",
        ),
        pytest.param(
            AgentPayloadEntity({"query": ""}),
            AgentPayloadExpected(422),
            id="empty",
        ),
        pytest.param(
            AgentPayloadEntity({"query": "  "}),
            AgentPayloadExpected(422),
            id="whitespace",
        ),
        pytest.param(
            AgentPayloadEntity({"query": None}),
            AgentPayloadExpected(422),
            id="null",
        ),
        pytest.param(
            AgentPayloadEntity({"query": 12}),
            AgentPayloadExpected(422),
            id="number",
        ),
        pytest.param(
            AgentPayloadEntity({"query": "x" * 4001}),
            AgentPayloadExpected(422),
            id="too_long",
        ),
        pytest.param(
            AgentPayloadEntity({"query": "hi", "thread_id": "other"}),
            AgentPayloadExpected(422),
            id="unexpected_thread",
        ),
    ],
)
def test_agent_router_rejects_invalid_payload(
    entity: AgentPayloadEntity,
    expected: AgentPayloadExpected,
) -> None:
    # Arrange
    app = FastAPI()
    app.include_router(create_agent_router(), prefix="/v1")
    client = TestClient(app)

    # Act
    response = client.post("/v1/agent/answer", json=entity.payload)

    # Assert
    assert response.status_code == expected.status_code, (
        f"Expected {expected.status_code}, got {response.status_code}: "
        f"{response.text}"
    )
