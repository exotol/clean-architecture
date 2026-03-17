from __future__ import annotations

from app.domain.entities.document import Document
from app.domain.interfaces.search_repository import ISearchRepository


class SearchRepository(ISearchRepository):
    """Search repository implementation (mock)."""

    async def search(self, query: str) -> list[Document]:
        """Search documents by query (mock implementation)."""
        _ = self  # Protocol requires instance method; used for future backend
        # Mock implementation
        # In a real scenario, this would call OpenSearch/Elasticsearch
        return [
            Document(text=f"Result for {query}", metadata={"source": "mock"}),
        ]
