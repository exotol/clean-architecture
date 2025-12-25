import pytest
from httpx import AsyncClient

from app.core.constants import HELLO_WORLD
from app.presentation.api.schemas.root import HelloWorld
from tests.schemas.e2e.api.root import RootEntity
from tests.schemas.e2e.api.root import RootExpected


@pytest.mark.anyio()
@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            RootEntity(path="/common/"),
            RootExpected(
                status_code=200, json_body=HelloWorld(message=HELLO_WORLD)
            ),
            id="root_success",
        ),
    ],
)
async def test_root_endpoint(
    client: AsyncClient,
    entity: RootEntity,
    expected: RootExpected,
) -> None:
    # Act
    response = await client.get(entity.path)

    # Assert
    assert response.status_code == expected.status_code, (
        f"Test failed, actual status = {response.status_code}, "
        f"but expected status was = {expected.status_code}"
    )
    assert response.json() == expected.json_body.model_dump(), (
        f"Test failed, actual json = {response.json()}, "
        f"but expected json was = {expected.json_body.model_dump()}"
    )
