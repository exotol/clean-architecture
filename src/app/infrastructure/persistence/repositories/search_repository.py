from app.domain.entities.document import Document


class SearchRepository:
    async def search(self, query: str) -> list[Document]:  # noqa: PLR6301
        # Mock implementation
        # In a real scenario, this would call OpenSearch/Elasticsearch
        return [
            Document(text=f"Result for {query}", metadata={"source": "mock"})
        ]
