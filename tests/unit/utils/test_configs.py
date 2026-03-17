"""Unit tests for config loading."""

from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

from dynaconf import Dynaconf

from app.utils.configs import get_http_client_config
from app.utils.configs import load_settings


def test_load_settings_returns_dynaconf() -> None:
    # Arrange

    # Act
    settings = load_settings()

    # Assert
    assert isinstance(settings, Dynaconf), (
        f"Expected load_settings() to return Dynaconf instance, "
        f"got {type(settings)}"
    )


def test_get_http_client_config_uses_load_settings_when_settings_none(
    ) -> None:
    # Arrange
    http_client = MagicMock()
    http_client.BASE_URL = "http://from-test"
    http_client.TIMEOUT_SECONDS = 12.0
    http_client.MAX_CONNECTIONS = 7
    http_client.MAX_KEEPALIVE_CONNECTIONS = 3
    http_client.KEEPALIVE_EXPIRY_SECONDS = 1.5

    mocked_settings = MagicMock()
    mocked_settings.HTTP_CLIENT = http_client

    with patch("app.utils.configs.load_settings") as mock_load_settings:
        mock_load_settings.return_value = mocked_settings

        # Act
        config = get_http_client_config()

        # Assert
        mock_load_settings.assert_called_once()
        assert config.base_url == http_client.BASE_URL, (
            f"Expected base_url={http_client.BASE_URL!r}, "
            f"got {config.base_url!r}"
        )
        assert config.timeout_seconds == http_client.TIMEOUT_SECONDS, (
            "Expected timeout_seconds from load_settings()"
        )
        assert config.max_connections == http_client.MAX_CONNECTIONS, (
            f"Expected max_connections={http_client.MAX_CONNECTIONS!r}, "
            f"got {config.max_connections!r}"
        )
        assert config.max_keepalive_connections == (
            http_client.MAX_KEEPALIVE_CONNECTIONS
        ), (
            "Expected max_keepalive_connections from load_settings()"
        )
        assert (
            config.keepalive_expiry_seconds
            == http_client.KEEPALIVE_EXPIRY_SECONDS
        ), (
            "Expected keepalive_expiry_seconds from load_settings()"
        )
