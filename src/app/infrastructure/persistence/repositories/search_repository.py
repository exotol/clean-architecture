from __future__ import annotations

from app.domain.entities.document import Document
from app.domain.interfaces.search_repository import ISearchRepository


class SearchRepository(ISearchRepository):
    """Search repository implementation (mock)."""

    async def search(self, query: str) -> list[Document]:  # noqa: PLR6301
        """Search documents by query (mock implementation)."""
        # Mock implementation
        # In a real scenario, this would call OpenSearch/Elasticsearch
        return [
            Document(text=f"Result for {query}", metadata={"source": "mock"}),
        ]
