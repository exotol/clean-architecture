import pytest
from httpx import AsyncClient

from app.core.constants import METRICS_REQUESTS_TOTAL_NAME


@pytest.mark.anyio()
async def test_metrics_endpoint(client: AsyncClient) -> None:
    """
    Test that the /common/metrics endpoint returns Prometheus metrics.
    """
    # 1. Make a request to generate some metrics
    response = await client.get("/common/healthcheck")
    assert response.status_code == 200

    # 2. Fetch metrics
    response = await client.get("/common/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"

    # 3. Verify content
    content = response.text
    assert METRICS_REQUESTS_TOTAL_NAME in content
    assert 'status="success"' in content
    assert 'event="HEALTHCHECK"' in content
