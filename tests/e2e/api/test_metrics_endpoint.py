import pytest
from httpx import AsyncClient

from app.core.constants import METRICS_REQUESTS_TOTAL_NAME
from tests.schemas.e2e.api.metrics import MetricsEntity
from tests.schemas.e2e.api.metrics import MetricsExpected


@pytest.mark.anyio()
@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            MetricsEntity(
                path="/common/metrics",
                trigger_path="/common/healthcheck",
            ),
            MetricsExpected(
                status_code=200,
                content_type="text/plain; charset=utf-8",
                contains=[
                    METRICS_REQUESTS_TOTAL_NAME,
                    'status="success"',
                    'event="HEALTHCHECK"',
                    'le="0.005"',
                ],
            ),
            id="metrics_success",
        ),
    ],
)
async def test_metrics_endpoint(
    client: AsyncClient,
    entity: MetricsEntity,
    expected: MetricsExpected,
) -> None:
    """
    Test that the /common/metrics endpoint returns Prometheus metrics.

    Args:
        client: Async HTTP client.
        entity: Test entity with paths.
        expected: Expected response data.
    """
    # 1. Make a request to generate some metrics
    trigger_response = await client.get(entity.trigger_path)
    assert trigger_response.status_code == 200

    # 2. Fetch metrics
    response = await client.get(entity.path)

    # 3. Assertions
    assert response.status_code == expected.status_code, (
        f"Test failed, actual status = {response.status_code}, "
        f"but expected status was = {expected.status_code}"
    )
    assert response.headers["content-type"] == expected.content_type, (
        f"Test failed, actual content-type = {response.headers.get("content-type")}, "
        f"but expected content-type was = {expected.content_type}"
    )

    content = response.text
    for item in expected.contains:
        assert item in content, (
            f"Test failed, expected '{item}' to be in response content, "
            f"but it was not found.\nContent snippet:\n{content[:500]}..."
        )
