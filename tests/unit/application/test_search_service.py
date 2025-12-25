from unittest.mock import AsyncMock

import pytest

from app.application.services.search_service import SearchService
from app.domain.entities.document import Document
from app.domain.interfaces.search_repository import ISearchRepository
from tests.schemas.unit.application.search_service import SearchServiceEntity
from tests.schemas.unit.application.search_service import SearchServiceExpected


@pytest.fixture()
def mock_repository() -> AsyncMock:
    return AsyncMock(spec=ISearchRepository)


@pytest.fixture()
def search_service(mock_repository: AsyncMock) -> SearchService:
    return SearchService(repository=mock_repository)


@pytest.mark.anyio()
@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            SearchServiceEntity(
                query="test",
                mock_return=[Document(text="res1"), Document(text="res2")],
            ),
            SearchServiceExpected(
                count=2, results=[Document(text="res1"), Document(text="res2")]
            ),
            id="success_multi_result",
        ),
        pytest.param(
            SearchServiceEntity(query="empty", mock_return=[]),
            SearchServiceExpected(count=0, results=[]),
            id="success_empty_result",
        ),
        pytest.param(
            SearchServiceEntity(
                query="single", mock_return=[Document(text="res1")]
            ),
            SearchServiceExpected(count=1, results=[Document(text="res1")]),
            id="success_single_result",
        ),
    ],
)
async def test_search_success(
    search_service: SearchService,
    mock_repository: AsyncMock,
    entity: SearchServiceEntity,
    expected: SearchServiceExpected,
) -> None:
    # Arrange
    mock_repository.search.return_value = entity.mock_return

    # Act
    actual_results = await search_service.search(query=entity.query)

    # Assert
    assert len(actual_results) == expected.count, (
        f"Test failed, actual count = {len(actual_results)}, "
        f"but expected count was = {expected.count}"
    )
    assert actual_results == expected.results, (
        f"Test failed, actual results = {actual_results}, "
        f"but expected results were = {expected.results}"
    )
