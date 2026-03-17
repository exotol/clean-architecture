"""Unit tests for liveness and readiness probes."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

from fastapi.responses import JSONResponse
import pytest

from app.presentation.api.common.endpoints.probes import liveness
from app.presentation.api.common.endpoints.probes import readiness
from app.presentation.api.schemas.healthcheck import Liveness
from app.presentation.api.schemas.healthcheck import Readiness
from tests.schemas.unit.presentation.api.common.probes import (
    ReadinessProbeEntity,
)
from tests.schemas.unit.presentation.api.common.probes import (
    ReadinessProbeExpected,
)


def test_liveness_returns_ok() -> None:
    """Liveness handler returns status ok."""
    # Act
    result = liveness()

    # Assert
    assert result == Liveness(), f"Expected Liveness(), got {result!r}"
    assert result.status == "ok", (
        f"Expected status 'ok', got {result.status!r}"
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            ReadinessProbeEntity(is_ready=True),
            ReadinessProbeExpected(
                returns_readiness_schema=True,
                status_code=None,
                body_status_value=None,
            ),
            id="ready_200",
        ),
        pytest.param(
            ReadinessProbeEntity(is_ready=False),
            ReadinessProbeExpected(
                returns_readiness_schema=False,
                status_code=503,
                body_status_value="not_ready",
            ),
            id="not_ready_503",
        ),
    ],
)
async def test_readiness(
    entity: ReadinessProbeEntity,
    expected: ReadinessProbeExpected,
) -> None:
    """Readiness handler returns Readiness when ready, 503 when not."""
    # Arrange
    mock_checker = AsyncMock()
    mock_checker.is_ready = AsyncMock(return_value=entity.is_ready)

    # Act
    result = await readiness(checker=mock_checker)

    # Assert
    if expected.returns_readiness_schema:
        assert result == Readiness(), f"Expected Readiness(), got {result!r}"
        assert result.status == "ok", (
            f"Expected status 'ok', got {result.status!r}"
        )
    else:
        assert isinstance(result, JSONResponse), (
            f"Expected JSONResponse, got {type(result)}"
        )
        assert result.status_code == expected.status_code, (
            f"Expected status_code {expected.status_code}, "
            f"got {result.status_code}"
        )
        assert result.body is not None, "Expected non-null body"
        body = json.loads(result.body)
        assert body.get("status") == expected.body_status_value, (
            f"Expected body status {expected.body_status_value!r}, "
            f"got {body!r}"
        )
