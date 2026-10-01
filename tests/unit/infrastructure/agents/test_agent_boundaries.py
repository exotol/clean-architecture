from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage
from langchain_core.messages import HumanMessage
from langchain_core.messages import ToolMessage
import pytest

from app.core.exceptions import BusinessError
from app.core.exceptions import InfrastructureError
from app.infrastructure.agents import LangGraphAgentRunner
from tests.schemas.unit.infrastructure.agent import AgentGuardEntity
from tests.schemas.unit.infrastructure.agent import AgentGuardExpected
from tests.schemas.unit.infrastructure.agent import ToolFailureEntity
from tests.schemas.unit.infrastructure.agent import ToolFailureExpected
from tests.unit.infrastructure.agents.test_langgraph_runner import (
    create_gateways,
)


if TYPE_CHECKING:
    from app.domain.entities.agent import AgentAnswer


async def run_guard_case(entity: AgentGuardEntity) -> AgentAnswer:
    gateways, _ = create_gateways()
    bound_model = MagicMock()
    bound_model.ainvoke = AsyncMock(return_value=entity.response)
    model = MagicMock()
    model.bind_tools.return_value = bound_model
    runner = LangGraphAgentRunner(
        model,
        gateways,
        max_steps=entity.max_steps,
        timeout_seconds=entity.timeout_seconds,
    )
    return await runner.run("Boundary check")


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            AgentGuardEntity(AIMessage(content="ok"), max_steps=1),
            AgentGuardExpected(ValueError, "max_steps"),
            id="invalid_step_limit",
        ),
        pytest.param(
            AgentGuardEntity(AIMessage(content="ok"), timeout_seconds=0),
            AgentGuardExpected(ValueError, "timeout_seconds"),
            id="invalid_timeout",
        ),
        pytest.param(
            AgentGuardEntity(HumanMessage(content="wrong role")),
            AgentGuardExpected(TypeError, "AIMessage"),
            id="unexpected_message_type",
        ),
        pytest.param(
            AgentGuardEntity(
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "web_search",
                            "args": {"query": "x"},
                            "id": str(i),
                        }
                        for i in range(5)
                    ],
                ),
            ),
            AgentGuardExpected(InfrastructureError, "too many tools"),
            id="too_many_tool_calls",
        ),
        pytest.param(
            AgentGuardEntity(AIMessage(content="   ")),
            AgentGuardExpected(InfrastructureError, "final answer"),
            id="empty_final_text",
        ),
        pytest.param(
            AgentGuardEntity(
                AIMessage(
                    content=[
                        {
                            "type": "reasoning",
                            "reasoning": "internal metadata",
                        },
                    ],
                ),
            ),
            AgentGuardExpected(InfrastructureError, "final answer"),
            id="reasoning_block_is_not_final_text",
        ),
        pytest.param(
            AgentGuardEntity(
                AIMessage(
                    content="",
                    tool_calls=[
                        {"name": "shell", "args": {}, "id": "bad-tool"},
                    ],
                ),
            ),
            AgentGuardExpected(InfrastructureError, "unknown tool"),
            id="unregistered_capability",
        ),
    ],
)
async def test_model_boundaries_fail_before_dispatch(
    entity: AgentGuardEntity,
    expected: AgentGuardExpected,
) -> None:
    # Arrange
    case = entity

    # Act
    with pytest.raises(expected.exception, match=expected.message) as error:
        await run_guard_case(case)

    # Assert
    assert isinstance(error.value, expected.exception), (
        f"Expected {expected.exception}, got {type(error.value)}"
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            ToolFailureEntity(
                "web_search",
                {"query": "docs"},
                InfrastructureError("Search unavailable"),
            ),
            ToolFailureExpected(recoverable=True),
            id="provider_failure",
        ),
        pytest.param(
            ToolFailureEntity(
                "web_search",
                {"query": "docs"},
                BusinessError("Unsupported query"),
            ),
            ToolFailureExpected(recoverable=True),
            id="business_failure",
        ),
        pytest.param(
            ToolFailureEntity("weather", {"latitude": 999, "longitude": 13}),
            ToolFailureExpected(recoverable=True),
            id="invalid_tool_arguments",
        ),
        pytest.param(
            ToolFailureEntity(
                "web_search",
                {"query": "docs"},
                ValueError("bug in adapter"),
            ),
            ToolFailureExpected(recoverable=False),
            id="programming_fault",
        ),
    ],
)
async def test_tool_error_policy_preserves_failure_boundaries(
    entity: ToolFailureEntity,
    expected: ToolFailureExpected,
) -> None:
    # Arrange
    gateways, search = create_gateways()
    search.search.side_effect = entity.error
    bound_model = MagicMock()
    bound_model.ainvoke = AsyncMock(
        side_effect=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": entity.name,
                        "args": entity.arguments,
                        "id": "tool-1",
                    },
                ],
            ),
            AIMessage(content="The requested data is unavailable."),
        ],
    )
    model = MagicMock()
    model.bind_tools.return_value = bound_model
    runner = LangGraphAgentRunner(
        model,
        gateways,
        max_steps=5,
        timeout_seconds=2,
    )

    # Act
    if expected.recoverable:
        answer = await runner.run("Use the tool")
    else:
        with pytest.raises(ValueError, match="bug in adapter"):
            await runner.run("Use the tool")
        answer = None

    # Assert
    if answer is not None:
        assert answer.tools_used == (), (
            f"Failed or rejected tools must not be successful: {answer}"
        )
        tool_messages = [
            message
            for message in bound_model.ainvoke.call_args.args[0]
            if isinstance(message, ToolMessage)
        ]
        assert len(tool_messages) == 1, (
            f"Expected one tool observation, got {tool_messages}"
        )
        assert tool_messages[0].status == "error", (
            f"Expected a failed tool observation, got {tool_messages[0]}"
        )
    else:
        assert bound_model.ainvoke.call_count == 1, (
            "Programming failures must interrupt the graph before retrying"
        )
