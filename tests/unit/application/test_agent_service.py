from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.application.services.agent_service import AgentService
from app.core.exceptions import BusinessError
from app.domain.entities.agent import AgentAnswer
from app.domain.interfaces.agent_runner import IAgentRunner
from tests.schemas.unit.application.agent import AgentServiceEntity
from tests.schemas.unit.application.agent import AgentServiceExpected


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            AgentServiceEntity(
                query="weather in Moscow",
                runner_result=AgentAnswer("Sunny", ("weather",)),
            ),
            AgentServiceExpected(
                result=AgentAnswer("Sunny", ("weather",)),
            ),
            id="valid_query",
        ),
        pytest.param(
            AgentServiceEntity(query=""),
            AgentServiceExpected(exception=BusinessError),
            id="empty_query",
        ),
        pytest.param(
            AgentServiceEntity(query="   "),
            AgentServiceExpected(exception=BusinessError),
            id="whitespace_query",
        ),
    ],
)
async def test_answer(
    entity: AgentServiceEntity,
    expected: AgentServiceExpected,
) -> None:
    # Arrange
    runner = AsyncMock(spec=IAgentRunner)
    runner.run.return_value = entity.runner_result
    service = AgentService(runner)

    # Act
    if expected.exception is not None:
        with pytest.raises(expected.exception):
            await service.answer(entity.query)
        actual = None
    else:
        actual = await service.answer(entity.query)

    # Assert
    assert actual == expected.result, (
        f"Expected result {expected.result}, got {actual}"
    )
    assert runner.run.call_count == int(expected.exception is None), (
        "Expected runner call count "
        f"{int(expected.exception is None)}, got {runner.run.call_count}"
    )
