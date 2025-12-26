from app.core.events import Events
from app.core.monitor import monitor
from app.domain.entities.document import Document
from app.domain.interfaces.search_repository import ISearchRepository


class SearchService:
    def __init__(self, repository: ISearchRepository) -> None:
        self._repository = repository

    @monitor(
        event_name=Events.SEARCH_SERVICE,
        use_log_args=True,
        use_log_result=True,
    )
    async def search(self, query: str) -> list[Document]:
        return await self._repository.search(query=query)
