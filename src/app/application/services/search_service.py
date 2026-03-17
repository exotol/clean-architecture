from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.events import Events
from app.utils.monitor import monitor


if TYPE_CHECKING:
    from app.domain.entities.document import Document
    from app.domain.interfaces.search_repository import ISearchRepository


class SearchService:
    """Use-case service for searching documents."""

    def __init__(self, repository: ISearchRepository) -> None:
        self._repository = repository

    @monitor(
        event_name=Events.SEARCH_SERVICE,
        use_log_args=True,
        use_log_result=True,
    )
    async def search(self, query: str) -> list[Document]:
        """Search documents by query."""
        return await self._repository.search(query=query)
