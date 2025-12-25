import pytest
from httpx import AsyncClient

from app.presentation.api.schemas.healthcheck import Healthcheck
from tests.schemas.e2e.api.healthcheck import HealthcheckEntity
from tests.schemas.e2e.api.healthcheck import HealthcheckExpected


@pytest.mark.anyio()
@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            HealthcheckEntity(path="/common/healthcheck"),
            HealthcheckExpected(status_code=200, json_body=Healthcheck()),
            id="healthcheck_success",
        ),
    ],
)
async def test_healthcheck_endpoint(
    client: AsyncClient,
    entity: HealthcheckEntity,
    expected: HealthcheckExpected,
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
