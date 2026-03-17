from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

from starlette.middleware import Middleware

from app.core.app_factory import create_app
from app.core.app_factory import create_middleware_list
from app.infrastructure.middleware.rate_limit import RateLimitStore
from app.utils.configs import ProfilingConfig
from app.utils.configs import RateLimitConfig
from app.utils.configs import SecurityConfig


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


def test_create_middleware_list() -> None:
    # Arrange
    security_config = SecurityConfig(
        trusted_hosts=["example.com"],
        cors_origins=["http://localhost"],
        cors_allow_credentials=True,
        cors_allow_methods=["GET"],
        cors_allow_headers=["*"],
    )
    profiling_config = ProfilingConfig(enabled=True)
    rate_limit_config = _rate_limit_config(enabled=False)
    rate_limit_store = RateLimitStore()

    # Act
    middleware = create_middleware_list(
        security_config,
        profiling_config,
        rate_limit_config,
        rate_limit_store,
    )

    # Assert
    assert isinstance(middleware, list)
    assert len(middleware) == 4  # Correlation, TrustedHost, CORS, Profiling
    assert isinstance(middleware[0], Middleware)


def test_create_middleware_list_no_profiling() -> None:
    # Arrange
    security_config = SecurityConfig(
        trusted_hosts=["*"],
        cors_origins=["*"],
        cors_allow_credentials=True,
        cors_allow_methods=["*"],
        cors_allow_headers=["*"],
    )
    profiling_config = ProfilingConfig(enabled=False)
    rate_limit_config = _rate_limit_config(enabled=False)
    rate_limit_store = RateLimitStore()

    # Act
    middleware = create_middleware_list(
        security_config,
        profiling_config,
        rate_limit_config,
        rate_limit_store,
    )

    # Assert
    assert len(middleware) == 3


def test_create_middleware_list_with_rate_limit() -> None:
    # Arrange
    security_config = SecurityConfig(
        trusted_hosts=["*"],
        cors_origins=["*"],
        cors_allow_credentials=True,
        cors_allow_methods=["*"],
        cors_allow_headers=["*"],
    )
    profiling_config = ProfilingConfig(enabled=False)
    rate_limit_config = _rate_limit_config(enabled=True)
    rate_limit_store = RateLimitStore()

    # Act
    middleware = create_middleware_list(
        security_config,
        profiling_config,
        rate_limit_config,
        rate_limit_store,
    )

    # Assert
    assert len(middleware) == 4  # + RateLimit


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
        # Mock create_middleware_list to keep this test focused on wiring.
        with patch(
            "app.core.app_factory.create_middleware_list",
        ) as mock_create_middleware:
            mock_create_middleware.return_value = []
            app = create_app()

        # Assert
        assert app is mock_app
        mock_setup_logging.assert_called_once()
        mock_setup_metrics.assert_called_once()
        mock_app.include_router.assert_called_once()

        # Verify container was stored in state
        assert mock_app.state.container == mock_container
