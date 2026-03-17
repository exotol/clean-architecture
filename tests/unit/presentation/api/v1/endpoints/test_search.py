"""Unit tests for search (generate_answer) endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.domain.entities.document import Document
from app.presentation.api.schemas.search import SearchRequest
from app.presentation.api.schemas.search import SearchResponse
from app.presentation.api.v1.endpoints.search import generate_answer


@pytest.mark.anyio
async def test_generate_answer_returns_search_response() -> None:
    """Endpoint calls search_service and returns SearchResponse."""
    # Arrange
    mock_search_service = AsyncMock()
    mock_search_service.search = AsyncMock(
        return_value=[
            Document(text="Result for q", metadata={"source": "mock"}),
        ],
    )
    request = SearchRequest(query="test query")

    # Act
    result = await generate_answer(
        request,
        search_service=mock_search_service,
    )

    # Assert
    assert isinstance(result, SearchResponse), (
        f"Expected SearchResponse, got {type(result)}"
    )
    assert len(result.documents) == 1, (
        f"Expected 1 document, got {len(result.documents)}"
    )
    assert result.documents[0].text == "Result for q", (
        f"Expected document text 'Result for q', "
        f"got {result.documents[0].text!r}"
    )
    assert mock_search_service.search.call_count == 1, (
        f"Expected search called once, "
        f"got {mock_search_service.search.call_count}"
    )
    mock_search_service.search.assert_called_with(query="test query")
