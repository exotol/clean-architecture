"""Unit tests for main entrypoint (main, init_server_container)."""

from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

from app.main import init_server_container
from app.main import main
from app.utils.configs import LoggerConfig
from app.utils.configs import LogLevel
from app.utils.configs import OTLPConfig


def test_init_server_container() -> None:
    # Arrange
    with (
        patch("app.main.ServerContainer") as mock_container_cls,
        patch("app.main.load_settings") as mock_load,
    ):
        mock_container = mock_container_cls.return_value
        mock_container.infra_container.config.from_dict = MagicMock()
        mock_load.return_value.as_dict.return_value = {}

        # Act
        init_server_container()

        # Assert
        assert mock_container_cls.call_count == 1, (
            f"Expected ServerContainer() called once, "
            f"got {mock_container_cls.call_count}"
        )
        mock_load.return_value.as_dict.assert_called_once()
        mock_container.infra_container.config.from_dict.assert_called_once_with(
            {},
        )


def test_main_calls_setup_logging_and_serve() -> None:
    # Arrange
    mock_server = MagicMock()
    logger_config = LoggerConfig(
        level=LogLevel.INFO,
        format="%(message)s",
        path=None,
        rotation="1d",
        retention="7d",
        loggers_to_root=[],
    )
    otlp_config = OTLPConfig(
        enabled=False,
        endpoint="",
        service_name="test",
        insecure=True,
    )

    # Act
    with patch("app.main.setup_logging") as mock_setup_logging:
        main(
            granian_server=mock_server,
            logger_config=logger_config,
            otlp_config=otlp_config,
        )

        # Assert
        assert mock_setup_logging.call_count == 1, (
            f"Expected setup_logging called once, "
            f"got {mock_setup_logging.call_count}"
        )
        mock_setup_logging.assert_called_once_with(
            logger_config=logger_config,
            otlp_config=otlp_config,
        )
        assert mock_server.serve.call_count == 1, (
            f"Expected server.serve() called once, "
            f"got {mock_server.serve.call_count}"
        )
