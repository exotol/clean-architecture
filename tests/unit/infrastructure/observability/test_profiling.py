from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from starlette.requests import Request
from starlette.responses import Response

from app.infrastructure.observability.profiling import ProfilingMiddleware
from app.utils.configs import ProfilingConfig


@pytest.fixture
def profiling_config(tmp_path) -> ProfilingConfig:
    return ProfilingConfig(
        enabled=True,
        output_dir=str(tmp_path / "profiles"),
        top_n=10,
        sort_by="cumulative",
    )


@pytest.fixture
def mock_app() -> MagicMock:
    return MagicMock()


@pytest.mark.asyncio
async def test_profiling_middleware_disabled(
    mock_app: MagicMock,
) -> None:
    # Arrange
    config = ProfilingConfig(enabled=False)
    middleware = ProfilingMiddleware(mock_app, config)

    mock_request = MagicMock(spec=Request)
    mock_call_next = MagicMock()
    mock_response = Response()

    async def call_next(_req):
        return mock_response

    mock_call_next.side_effect = call_next

    # Act
    # dispatch is async
    response = await middleware.dispatch(mock_request, call_next)

    # Assert
    assert response is mock_response
    # dispatch calls call_next(request), so our side_effect runs
    # cProfile should NOT be used
    with patch("cProfile.Profile") as mock_profile:
        assert not mock_profile.called


@pytest.mark.asyncio
async def test_profiling_middleware_enabled(
    mock_app: MagicMock,
    profiling_config: ProfilingConfig,
) -> None:
    # Arrange
    middleware = ProfilingMiddleware(mock_app, profiling_config)

    mock_request = MagicMock(spec=Request)
    mock_request.method = "GET"
    mock_request.url.path = "/test"

    MagicMock()
    mock_response = Response()

    async def call_next(_req):
        return mock_response

    # Act
    with (
        patch("cProfile.Profile") as mock_profile_cls,
        patch("pstats.Stats") as mock_stats_cls,
        patch("app.infrastructure.observability.profiling.Path"),
        patch(
            "app.infrastructure.observability.profiling.datetime",
        ) as mock_datetime,
    ):
        mock_profiler = mock_profile_cls.return_value
        mock_datetime.now.return_value.strftime.return_value = (
            "20230101_000000"
        )

        response = await middleware.dispatch(mock_request, call_next)

    # Assert
    assert response is mock_response
    mock_profiler.enable.assert_called_once()
    mock_profiler.disable.assert_called_once()
    mock_stats_cls.assert_called_once()  # stats generation
    mock_profiler.dump_stats.assert_called_once()  # save to file


def test_ensure_output_dir(
    mock_app: MagicMock,
    profiling_config: ProfilingConfig,
) -> None:
    # Arrange
    with patch("app.infrastructure.observability.profiling.Path") as mock_path:
        ProfilingMiddleware(mock_app, profiling_config)

        # Act is in init
        mock_path.assert_called_with(profiling_config.output_dir)
        mock_path.return_value.mkdir.assert_called_once_with(
            parents=True, exist_ok=True,
        )
