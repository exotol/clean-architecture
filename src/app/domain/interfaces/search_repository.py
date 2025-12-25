from typing import Protocol
from typing import runtime_checkable

from app.domain.entities.document import Document


@runtime_checkable
class ISearchRepository(Protocol):
    """Interface for search repository implementations."""

    async def search(self, query: str) -> list[Document]:
        """
        Search for data in the repository.

        Args:
            query: Search query string.
        """
