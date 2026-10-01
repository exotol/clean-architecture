from __future__ import annotations

import asyncio
from threading import Event
from unittest.mock import patch

import pytest

from app.infrastructure.gateways.agent_tools import DuckDuckGoSearchGateway
from tests.unit.infrastructure.gateways.test_agent_tools import (
    FakeSearchClient,
)


class BlockingSearchClient:
    """Keep the first worker alive after cancellation of its async caller."""

    def __init__(self) -> None:
        self.started = Event()
        self.release = Event()
        self.finished = Event()

    def text(self, query, *, backend, max_results) -> list[dict[str, object]]:
        del query, backend, max_results
        self.started.set()
        self.release.wait(timeout=2)
        self.finished.set()
        return []


@pytest.mark.anyio
async def test_cancelled_search_does_not_share_client_with_next_request() -> (
    None
):
    # Arrange
    first_client = BlockingSearchClient()
    second_client = FakeSearchClient([])
    with patch(
        "app.infrastructure.gateways.agent_tools.DDGS",
        side_effect=[first_client, second_client],
    ) as factory:
        gateway = DuckDuckGoSearchGateway(timeout_seconds=1)
        first_task = asyncio.create_task(gateway.search("first"))
        started = await asyncio.to_thread(first_client.started.wait, 1)

        # Act
        try:
            first_task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await first_task
            second_result = await gateway.search("second")
            first_still_running = not first_client.finished.is_set()
        finally:
            first_client.release.set()
            await asyncio.to_thread(first_client.finished.wait, 2)

    # Assert
    assert started, "Expected the first search worker to enter text()"
    assert first_still_running, (
        "Cancellation must not be mistaken for termination of the worker"
    )
    assert factory.call_count == 2, (
        f"Expected independent clients, got {factory.call_count} creations"
    )
    assert second_client.query == "second", (
        f"Next request used an unexpected client: {second_client.query}"
    )
    assert second_result == (), (
        f"Expected empty result from the second client, got {second_result}"
    )
