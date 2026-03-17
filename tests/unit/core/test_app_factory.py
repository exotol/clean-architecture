from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

import anyio
import pytest
from starlette.middleware import Middleware

from app.core import app_factory
from app.core.app_factory import app_lifespan
from app.core.app_factory import create_app
from app.core.app_factory import create_middleware_list
from app.infrastructure.middleware.rate_limit import RateLimitStore
from app.utils.configs import ProfilingConfig
from app.utils.configs import RateLimitConfig
from app.utils.configs import SecurityConfig
from tests.schemas.unit.core.app_factory import MiddlewareListEntity
from tests.schemas.unit.core.app_factory import MiddlewareListExpected


def _rate_limit_config(
    *,
    enabled: bool = False,
) -> RateLimitConfig:
    return RateLimitConfig(
        enabled=enabled,
        requests_per_window=100,
        window_seconds=60.0,
        key_header=None,
    )


def _security_config() -> SecurityConfig:
    return SecurityConfig(
        trusted_hosts=["*"],
        cors_origins=["*"],
        cors_allow_credentials=True,
        cors_allow_methods=["*"],
        cors_allow_headers=["*"],
    )


@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            MiddlewareListEntity(
                profiling_enabled=True,
                rate_limit_enabled=False,
            ),
            MiddlewareListExpected(middleware_count=4),
            id="profiling_on_rate_limit_off",
        ),
        pytest.param(
            MiddlewareListEntity(
                profiling_enabled=False,
                rate_limit_enabled=False,
            ),
            MiddlewareListExpected(middleware_count=3),
            id="profiling_off_rate_limit_off",
        ),
        pytest.param(
            MiddlewareListEntity(
                profiling_enabled=False,
                rate_limit_enabled=True,
            ),
            MiddlewareListExpected(middleware_count=4),
            id="profiling_off_rate_limit_on",
        ),
    ],
)
def test_create_middleware_list(
    entity: MiddlewareListEntity,
    expected: MiddlewareListExpected,
) -> None:
    """Middleware list length depends on profiling and rate_limit config."""
    # Arrange
    security_config = _security_config()
    profiling_config = ProfilingConfig(enabled=entity.profiling_enabled)
    rate_limit_config = _rate_limit_config(enabled=entity.rate_limit_enabled)
    rate_limit_store = RateLimitStore()

    # Act
    middleware = create_middleware_list(
        security_config,
        profiling_config,
        rate_limit_config,
        rate_limit_store,
    )

    # Assert
    assert isinstance(middleware, list), (
        f"Expected middleware to be list, got {type(middleware)}"
    )
    assert len(middleware) == expected.middleware_count, (
        f"Expected {expected.middleware_count} middlewares, "
        f"got {len(middleware)}"
    )
    assert isinstance(middleware[0], Middleware), (
        f"Expected first item to be Middleware, got {type(middleware[0])}"
    )


def test_create_app() -> None:
    # Arrange
    with (
        patch("app.core.app_factory.AppContainer") as mock_container_cls,
        patch("app.core.app_factory.load_settings"),
        patch("app.core.app_factory.setup_logging") as mock_setup_logging,
        patch("app.core.app_factory.setup_metrics") as mock_setup_metrics,
        patch("app.core.app_factory.FastAPI") as mock_fastapi_cls,
    ):
        mock_container = mock_container_cls.return_value
        mock_container.infra_container.config.from_dict = MagicMock()

        mock_app = MagicMock()
        mock_fastapi_cls.return_value = mock_app

        # Act
        with patch(
            "app.core.app_factory.create_middleware_list",
        ) as mock_create_middleware:
            mock_create_middleware.return_value = []
            app = create_app()

        # Assert
        assert app is mock_app, (
            "Expected create_app() to return FastAPI instance from mock"
        )
        assert mock_setup_logging.call_count == 1, (
            f"Expected setup_logging called once, "
            f"got {mock_setup_logging.call_count}"
        )
        assert mock_setup_metrics.call_count == 1, (
            f"Expected setup_metrics called once, "
            f"got {mock_setup_metrics.call_count}"
        )
        assert mock_app.include_router.call_count == 1, (
            f"Expected include_router called once, "
            f"got {mock_app.include_router.call_count}"
        )
        assert mock_app.state.container == mock_container, (
            "Expected container to be stored in app.state"
        )


@pytest.mark.anyio
async def test_app_lifespan_init_and_shutdown_resources() -> None:
    # Arrange
    mock_app = MagicMock()
    mock_app.state = MagicMock()

    mock_container = MagicMock()
    mock_container.wire = MagicMock()
    mock_container.unwire = MagicMock()

    mock_infra = MagicMock()
    init_result = anyio.lowlevel.checkpoint()
    shutdown_result = anyio.lowlevel.checkpoint()
    mock_infra.init_resources.return_value = init_result
    mock_infra.shutdown_resources.return_value = shutdown_result
    mock_container.infra_container.return_value = mock_infra

    with patch("app.core.app_factory._ensure_observability") as mock_ensure:
        mock_ensure.return_value = None

        # Act
        async with app_lifespan(mock_app, mock_container):
            pass

        # Assert
        assert mock_container.wire.call_count == 1, (
            f"Expected container.wire called once, got "
            f"{mock_container.wire.call_count}"
        )
        assert mock_container.unwire.call_count == 1, (
            f"Expected container.unwire called once, got "
            f"{mock_container.unwire.call_count}"
        )
        assert mock_ensure.call_count == 1, (
            f"Expected _ensure_observability called once, got "
            f"{mock_ensure.call_count}"
        )
        mock_infra.init_resources.assert_called_once()
        mock_infra.shutdown_resources.assert_called_once()


def test_ensure_observability_tuple_execution() -> None:
    # Arrange
    logging_strategy = MagicMock()
    tracing_strategy = MagicMock()
    metrics_strategy = MagicMock()

    # Act
    result = app_factory._ensure_observability(
        logging_strategy=logging_strategy,
        tracing_strategy=tracing_strategy,
        metrics_strategy=metrics_strategy,
    )

    # Assert
    assert result is None, (
        f"Expected None from _ensure_observability, got {result!r}"
    )
