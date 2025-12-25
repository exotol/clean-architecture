import pytest
from httpx import AsyncClient

from app.presentation.api.schemas.search import SearchRequest
from tests.schemas.e2e.api.search import InvalidSearchEntity
from tests.schemas.e2e.api.search import InvalidSearchExpected
from tests.schemas.e2e.api.search import SearchExpected


@pytest.mark.anyio()
@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            SearchRequest(query="integration test"),
            SearchExpected(status_code=200, text_part="integration test"),
            id="valid_query_integration_test",
        ),
        pytest.param(
            SearchRequest(query="another query"),
            SearchExpected(status_code=200, text_part="another query"),
            id="valid_query_another_query",
        ),
        pytest.param(
            SearchRequest(query=""),
            SearchExpected(status_code=200, text_part="Result for "),
            id="valid_query_empty",
        ),
        pytest.param(
            SearchRequest(query="e2e test"),
            SearchExpected(status_code=200, text_part="Result for e2e test"),
            id="valid_query_e2e_scenario",
        ),
    ],
)
async def test_search_endpoint_success(
    client: AsyncClient,
    entity: SearchRequest,
    expected: SearchExpected,
) -> None:
    # Act
    response = await client.post(
        "/v1/answer/generate", json=entity.model_dump()
    )

    # Assert
    assert response.status_code == expected.status_code, (
        f"Test failed, actual status = {response.status_code}, "
        f"but expected status was = {expected.status_code}"
    )

    data = response.json()
    assert "hello" in data, (
        f"Test failed, actual keys = {list(data.keys())}, "
        f"but expected key 'hello' to be present"
    )

    inner_data = data["hello"]
    assert "documents" in inner_data, (
        f"Test failed, actual inner keys = {list(inner_data.keys())}, "
        f"but expected key 'documents' to be present"
    )

    assert len(inner_data["documents"]) == 1, (
        f"Test failed, actual document "
        f"count = {len(inner_data["documents"])}, "
        f"but expected count was = 1"
    )

    if expected.text_part:
        first_doc = inner_data["documents"][0]
        assert expected.text_part in first_doc["text"], (
            f"Test failed, actual text = {first_doc["text"]}, "
            f"but expected to contain = {expected.text_part}"
        )


@pytest.mark.anyio()
@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            InvalidSearchEntity(payload={}),
            InvalidSearchExpected(status_code=422),
            id="missing_query_field",
        ),
    ],
)
async def test_search_endpoint_invalid_payload(
    client: AsyncClient,
    entity: InvalidSearchEntity,
    expected: InvalidSearchExpected,
) -> None:
    # Act
    response = await client.post("/v1/answer/generate", json=entity.payload)

    # Assert
    assert response.status_code == expected.status_code, (
        f"Test failed, actual status = {response.status_code}, "
        f"but expected status was = {expected.status_code}"
    )
