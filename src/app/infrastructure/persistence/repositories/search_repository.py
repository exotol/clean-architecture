from app.domain.entities.document import Document


from app.domain.interfaces.search_repository import ISearchRepository


class SearchRepository(ISearchRepository):
    async def search(self, query: str) -> list[Document]:  # noqa: PLR6301
        # Mock implementation
        # In a real scenario, this would call OpenSearch/Elasticsearch
        return [
            Document(text=f"Result for {query}", metadata={"source": "mock"})
        ]
