import pytest

from app.domain.entities.document import Document
from app.infrastructure.persistence.repositories.search_repository import (
    SearchRepository,
)
from tests.schemas.integration.infrastructure.search_repository import (
    SearchRepoEntity,
)
from tests.schemas.integration.infrastructure.search_repository import (
    SearchRepoExpected,
)


@pytest.fixture()
def repository() -> SearchRepository:
    return SearchRepository()


@pytest.mark.anyio()
@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            SearchRepoEntity(query="hello"),
            SearchRepoExpected(
                count=1,
                text_part="Result for hello",
                metadata={"source": "mock"},
            ),
            id="search_hello",
        ),
        pytest.param(
            SearchRepoEntity(query="world"),
            SearchRepoExpected(
                count=1,
                text_part="Result for world",
                metadata={"source": "mock"},
            ),
            id="search_world",
        ),
        pytest.param(
            SearchRepoEntity(query=""),
            SearchRepoExpected(
                count=1, text_part="Result for ", metadata={"source": "mock"}
            ),
            id="search_empty",
        ),
    ],
)
async def test_search_repository_returns_mock_data(
    repository: SearchRepository,
    entity: SearchRepoEntity,
    expected: SearchRepoExpected,
) -> None:
    # Act
    actual_results = await repository.search(query=entity.query)

    # Assert
    assert len(actual_results) == expected.count, (
        f"Test failed, actual count = {len(actual_results)}, "
        f"but expected count was = {expected.count}"
    )

    actual_doc = actual_results[0]
    assert isinstance(actual_doc, Document), (
        f"Test failed, actual type = {type(actual_doc)}, "
        f"but expected type was = Document"
    )

    assert expected.text_part in actual_doc.text, (
        f"Test failed, actual text = {actual_doc.text}, "
        f"but expected to contain = {expected.text_part}"
    )

    assert actual_doc.metadata == expected.metadata, (
        f"Test failed, actual metadata = {actual_doc.metadata}, "
        f"but expected metadata was = {expected.metadata}"
    )
