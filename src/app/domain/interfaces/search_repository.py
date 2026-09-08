from __future__ import annotations

from abc import ABC
from abc import abstractmethod
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from app.domain.entities.document import Document


class ISearchRepository(ABC):
    """Interface for search repository implementations."""

    @abstractmethod
    async def search(self, query: str) -> list[Document]:
        """Search for data in the repository.

        Args:
            query: Search query string.
        """
