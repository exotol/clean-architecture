from __future__ import annotations

from unittest.mock import patch

import httpx
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
import pytest

from app.core.exceptions import InfrastructureError
from app.infrastructure.agents.resource import AgentRunnerResource
from app.utils.agent_config import AgentConfig
from tests.schemas.unit.core.agent import AgentConfigEntity
from tests.schemas.unit.core.agent import AgentConfigExpected


def create_config(
    *,
    enabled: bool = True,
    api_key: str = "test-key",
) -> AgentConfig:
    return AgentConfig(
        enabled=enabled,
        api_key=SecretStr(api_key),
        model="test-model",
        base_url="https://model.example/v1",
        model_timeout_seconds=2,
        run_timeout_seconds=5,
        max_steps=12,
        max_tokens=300,
        tool_timeout_seconds=1,
        geocoding_url="https://geocoding.example",
        weather_url="https://weather.example",
        currency_url="https://currency.example",
    )


class ModelTransport:
    """A real ChatOpenAI protocol exchange backed by an offline transport."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    def respond(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(
            200,
            json={
                "id": "offline-completion",
                "object": "chat.completion",
                "created": 0,
                "model": "test-model",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "Offline answer",
                        },
                        "finish_reason": "stop",
                    },
                ],
            },
        )


async def run_unavailable_resource(
    resource: AgentRunnerResource,
    config: AgentConfig,
    client: httpx.AsyncClient,
) -> None:
    runner = await resource.init(config, client)
    await runner.run("Hello")


@pytest.mark.anyio
async def test_resource_uses_real_model_adapter_and_closes_owned_client() -> (
    None
):
    # Arrange
    transport = ModelTransport()
    config = create_config()
    resource = AgentRunnerResource()
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(transport.respond),
    ) as shared_client:
        with patch(
            "app.infrastructure.agents.resource.ChatOpenAI",
            wraps=ChatOpenAI,
        ) as model_factory:
            runner = await resource.init(config, shared_client)
            owned_client = model_factory.call_args.kwargs["http_client"]

        # Act
        answer = await runner.run("A short greeting")
        await resource.shutdown(runner)

        # Assert
        assert answer.answer == "Offline answer", (
            f"Expected model response, got {answer.answer!r}"
        )
        assert answer.tools_used == (), (
            f"Expected no tools for final answer, got {answer.tools_used}"
        )
        assert len(transport.requests) == 1, (
            f"Expected one model call, got {len(transport.requests)}"
        )
        assert transport.requests[0].url.path == "/v1/chat/completions", (
            f"Unexpected model endpoint: {transport.requests[0].url}"
        )
        assert owned_client.is_closed, "Owned sync client must be closed"
        assert not shared_client.is_closed, (
            "Shared async client must remain owned by the outer DI resource"
        )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            AgentConfigEntity(enabled=False, api_key=""),
            AgentConfigExpected(fails_during_init=False),
            id="disabled_without_key",
        ),
        pytest.param(
            AgentConfigEntity(enabled=False, api_key="test-key"),
            AgentConfigExpected(fails_during_init=False),
            id="disabled_with_unused_key",
        ),
        pytest.param(
            AgentConfigEntity(enabled=True, api_key=""),
            AgentConfigExpected(fails_during_init=True),
            id="enabled_missing_key",
        ),
        pytest.param(
            AgentConfigEntity(enabled=True, api_key="  "),
            AgentConfigExpected(fails_during_init=True),
            id="enabled_whitespace_key",
        ),
    ],
)
async def test_resource_unavailable_without_configured_model(
    entity: AgentConfigEntity,
    expected: AgentConfigExpected,
) -> None:
    # Arrange
    config = create_config(enabled=entity.enabled, api_key=entity.api_key)
    resource = AgentRunnerResource()
    async with httpx.AsyncClient() as client:
        with patch("app.infrastructure.agents.resource.ChatOpenAI") as model:
            # Act
            with pytest.raises(InfrastructureError) as captured:
                await run_unavailable_resource(resource, config, client)
            await resource.shutdown(None)

            # Assert
            assert model.call_count == 0, (
                f"Unavailable agent created {model.call_count} model clients"
            )
            assert captured.value.service_name == "agent", (
                f"Expected agent failure, got {captured.value.service_name}"
            )
            assert ("required" in str(captured.value)) is (
                expected.fails_during_init
            ), f"Unexpected availability failure: {captured.value}"


@pytest.mark.anyio
async def test_resource_closes_client_when_graph_construction_fails() -> None:
    # Arrange
    resource = AgentRunnerResource()
    async with httpx.AsyncClient() as client:
        with (
            patch(
                "app.infrastructure.agents.resource.ChatOpenAI",
                wraps=ChatOpenAI,
            ) as model_factory,
            patch(
                "app.infrastructure.agents.resource.LangGraphAgentRunner",
                side_effect=ValueError("invalid graph"),
            ),
        ):
            # Act
            with pytest.raises(ValueError, match="invalid graph"):
                await resource.init(create_config(), client)

            # Assert
            assert model_factory.call_args.kwargs["http_client"].is_closed, (
                "Partial initialization must close the owned client"
            )
            assert not client.is_closed, (
                "Partial initialization must not close a borrowed client"
            )
