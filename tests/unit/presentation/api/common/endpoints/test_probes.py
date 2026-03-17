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


def test_liveness_returns_ok() -> None:
    """Liveness handler returns status ok."""
    result = liveness()
    assert result == Liveness()
    assert result.status == "ok"


@pytest.mark.anyio
async def test_readiness_returns_200_when_ready() -> None:
    """Readiness handler returns Readiness when checker is ready."""
    mock_checker = AsyncMock()
    mock_checker.is_ready = AsyncMock(return_value=True)
    result = await readiness(checker=mock_checker)
    assert result == Readiness()
    assert result.status == "ok"


@pytest.mark.anyio
async def test_readiness_returns_503_when_not_ready() -> None:
    """Readiness returns 503 when checker reports not ready."""
    mock_checker = AsyncMock()
    mock_checker.is_ready = AsyncMock(return_value=False)
    result = await readiness(checker=mock_checker)
    assert isinstance(result, JSONResponse)
    assert result.status_code == 503
    assert result.body is not None
    assert json.loads(result.body) == {"status": "not_ready"}
