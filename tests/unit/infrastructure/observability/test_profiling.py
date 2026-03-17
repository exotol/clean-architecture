from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from starlette.requests import Request
from starlette.responses import Response

from app.infrastructure.observability.profiling import ProfilingMiddleware
from app.utils.configs import ProfilingConfig
from tests.schemas.unit.infrastructure.observability.profiling import (
    ProfilingDispatchEntity,
)
from tests.schemas.unit.infrastructure.observability.profiling import (
    ProfilingDispatchExpected,
)


@pytest.fixture
def profiling_config(tmp_path: pytest.TempPathFactory) -> ProfilingConfig:
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
@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            ProfilingDispatchEntity(enabled=False),
            ProfilingDispatchExpected(
                profiler_enable_calls=0,
                profiler_disable_calls=0,
            ),
            id="disabled",
        ),
        pytest.param(
            ProfilingDispatchEntity(enabled=True),
            ProfilingDispatchExpected(
                profiler_enable_calls=1,
                profiler_disable_calls=1,
            ),
            id="enabled",
        ),
    ],
)
async def test_profiling_middleware_dispatch(
    mock_app: MagicMock,
    entity: ProfilingDispatchEntity,
    expected: ProfilingDispatchExpected,
    tmp_path: pytest.TempPathFactory,
) -> None:
    """Dispatch passes through response; when enabled, profiler is used."""
    # Arrange
    config = ProfilingConfig(
        enabled=entity.enabled,
        output_dir=str(tmp_path / "profiles"),
        top_n=10,
        sort_by="cumulative",
    )
    middleware = ProfilingMiddleware(mock_app, config)

    mock_request = MagicMock(spec=Request)
    mock_request.method = "GET"
    mock_request.url.path = "/test"
    mock_response = Response()

    async def call_next(_req: Request) -> Response:
        return mock_response

    mock_call_next = MagicMock()
    mock_call_next.side_effect = call_next

    # Act
    if entity.enabled:
        with (
            patch("cProfile.Profile") as mock_profile_cls,
            patch("pstats.Stats"),
            patch("app.infrastructure.observability.profiling.Path"),
            patch(
                "app.infrastructure.observability.profiling.datetime",
            ) as mock_datetime,
        ):
            mock_profiler = mock_profile_cls.return_value
            mock_datetime.now.return_value.strftime.return_value = (
                "20230101_000000"
            )
            response = await middleware.dispatch(
                mock_request,
                mock_call_next,
            )
    else:
        response = await middleware.dispatch(mock_request, mock_call_next)

    # Assert
    assert response is mock_response, (
        f"Expected pass-through response, got {type(response)}"
    )
    if entity.enabled:
        enable_calls = expected.profiler_enable_calls
        assert mock_profiler.enable.call_count == enable_calls, (
            f"Expected profiler.enable called {enable_calls} times, "
            f"got {mock_profiler.enable.call_count}"
        )
        assert mock_profiler.disable.call_count == (
            expected.profiler_disable_calls
        ), (
            f"Expected profiler.disable called "
            f"{expected.profiler_disable_calls} times, "
            f"got {mock_profiler.disable.call_count}"
        )


def test_ensure_output_dir(
    mock_app: MagicMock,
    profiling_config: ProfilingConfig,
) -> None:
    # Arrange
    with patch("app.infrastructure.observability.profiling.Path") as mock_path:
        # Act
        ProfilingMiddleware(mock_app, profiling_config)

        # Assert
        mock_path.assert_called_with(profiling_config.output_dir)
        mock_path.return_value.mkdir.assert_called_once_with(
            parents=True,
            exist_ok=True,
        )
