"""Unit tests for search (generate_answer) endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.domain.entities.document import Document
from app.presentation.api.schemas.search import SearchRequest
from app.presentation.api.v1.endpoints.search import generate_answer


@pytest.mark.anyio
async def test_generate_answer_returns_hello_response() -> None:
    """Endpoint calls search_service and returns mapped response."""
    mock_search_service = AsyncMock()
    mock_search_service.search = AsyncMock(
        return_value=[
            Document(text="Result for q", metadata={"source": "mock"}),
        ],
    )
    request = SearchRequest(query="test query")
    result = await generate_answer(
        request,
        search_service=mock_search_service,
    )
    assert "hello" in result
    resp = result["hello"]
    assert len(resp.documents) == 1
    assert resp.documents[0].text == "Result for q"
    mock_search_service.search.assert_called_once_with(query="test query")
