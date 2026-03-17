"""Unit tests for SearchRepository."""

from __future__ import annotations

import pytest

from app.domain.entities.document import Document
from app.infrastructure.persistence.repositories.search_repository import (
    SearchRepository,
)
from tests.schemas.unit.infrastructure.persistence.search_repository import (
    SearchRepoEntity,
)
from tests.schemas.unit.infrastructure.persistence.search_repository import (
    SearchRepoExpected,
)


@pytest.fixture
def repository() -> SearchRepository:
    return SearchRepository()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            SearchRepoEntity(query="test"),
            SearchRepoExpected(
                count=1,
                text_part="Result for test",
                metadata={"source": "mock"},
            ),
            id="query_test",
        ),
        pytest.param(
            SearchRepoEntity(query="hello"),
            SearchRepoExpected(
                count=1,
                text_part="Result for hello",
                metadata={"source": "mock"},
            ),
            id="query_hello",
        ),
        pytest.param(
            SearchRepoEntity(query=""),
            SearchRepoExpected(
                count=1,
                text_part="Result for ",
                metadata={"source": "mock"},
            ),
            id="query_empty",
        ),
    ],
)
async def test_search_returns_mock_documents(
    repository: SearchRepository,
    entity: SearchRepoEntity,
    expected: SearchRepoExpected,
) -> None:
    """Search returns one mock document; text contains query, metadata mock."""
    # Act
    results = await repository.search(query=entity.query)

    # Assert
    assert len(results) == expected.count, (
        f"Expected {expected.count} mock document(s), got {len(results)}"
    )
    assert isinstance(results[0], Document), (
        f"Expected first item to be Document, got {type(results[0])}"
    )
    assert expected.text_part in results[0].text, (
        f"Expected text to contain {expected.text_part!r}, "
        f"got {results[0].text!r}"
    )
    assert results[0].metadata == expected.metadata, (
        f"Expected metadata {expected.metadata!r}, got {results[0].metadata!r}"
    )
