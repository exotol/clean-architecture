"""Unit tests for SearchRepository."""

from __future__ import annotations

import pytest

from app.domain.entities.document import Document
from app.infrastructure.persistence.repositories.search_repository import (
    SearchRepository,
)


@pytest.fixture
def repository() -> SearchRepository:
    return SearchRepository()


@pytest.mark.anyio
async def test_search_returns_mock_documents(
    repository: SearchRepository,
) -> None:
    """search() returns list of Document with mock data."""
    results = await repository.search(query="test")
    assert len(results) == 1
    assert isinstance(results[0], Document)
    assert "Result for test" in results[0].text
    assert results[0].metadata == {"source": "mock"}
