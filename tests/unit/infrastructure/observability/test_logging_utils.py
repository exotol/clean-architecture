import logging
import sys
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from opentelemetry import trace
from pythonjsonlogger import jsonlogger

from app.infrastructure.observability.logging import setup_logging
from app.utils.configs import LoggerConfig
from app.utils.configs import LogLevel
from app.utils.configs import OTLPConfig
from tests.schemas.unit.infrastructure.logging import LoggingEntity
from tests.schemas.unit.infrastructure.logging import LoggingExpected


@pytest.fixture
def mock_trace_provider():
    with patch("app.infrastructure.observability.logging.trace.get_tracer_provider") as mock:
        yield mock


@pytest.fixture
def mock_set_tracer_provider():
    with patch("app.infrastructure.observability.logging.trace.set_tracer_provider") as mock:
        yield mock


@pytest.fixture
def mock_dict_config():
    with patch("app.infrastructure.observability.logging.logging.config.dictConfig") as mock:
        yield mock


@pytest.fixture
def mock_instrumentor():
    with patch("app.infrastructure.observability.logging.LoggingInstrumentor") as mock:
        yield mock


@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            LoggingEntity(
                logger_config=LoggerConfig(
                    level=LogLevel.INFO,
                    format="%(message)s",
                    path=None,
                    rotation="10 MB",
                    retention="10 days",
                    loggers_to_root=[],
                ),
                otlp_config=OTLPConfig(
                    enabled=False,
                    endpoint="",
                    service_name="test-service",
                    insecure=True,
                ),
            ),
            LoggingExpected(),
            id="success_local_logger_no_otlp",
        ),
        pytest.param(
            LoggingEntity(
                logger_config=LoggerConfig(
                    level=LogLevel.DEBUG,
                    format="%(message)s",
                    path="/tmp/logs.json",
                    rotation="1 day",
                    retention="1 week",
                    loggers_to_root=["uvicorn"],
                ),
                otlp_config=OTLPConfig(
                    enabled=True,
                    endpoint="console",
                    service_name="test-service",
                    insecure=True,
                ),
            ),
            LoggingExpected(
                trace_provider_set=True,
                logger_configured=True,
            ),
            id="success_file_logger_with_local_otlp",
        ),
    ],
)
def test_setup_logging(
    entity: LoggingEntity,
    expected: LoggingExpected,
    mock_trace_provider: MagicMock,
    mock_set_tracer_provider: MagicMock,
    mock_dict_config: MagicMock,
    mock_instrumentor: MagicMock,
) -> None:
    # Arrange
    # Define dummy classes to simulate types for isinstance checks
    class MockTracerProvider:
        def __init__(self, resource=None): pass
        def add_span_processor(self, processor): pass

    class MockBatchSpanProcessor:
        def __init__(self, exporter): pass

    class MockOTLPSpanExporter:
        def __init__(self, endpoint=None, insecure=None): pass

    class MockConsoleSpanExporter:
        def __init__(self): pass

    class MockResource:
        @staticmethod
        def create(attributes): return MagicMock()

    mock_trace_provider.return_value = None 
    
    with patch("app.infrastructure.observability.logging.TracerProvider", new=MockTracerProvider), \
         patch("app.infrastructure.observability.logging.BatchSpanProcessor", new=MockBatchSpanProcessor), \
         patch("app.infrastructure.observability.logging.OTLPSpanExporter", new=MockOTLPSpanExporter), \
         patch("app.infrastructure.observability.logging.ConsoleSpanExporter", new=MockConsoleSpanExporter), \
         patch("app.infrastructure.observability.logging.Resource", new=MockResource):

        # Act
        setup_logging(entity.logger_config, entity.otlp_config)

        # Assert
        if expected.trace_provider_set:
            mock_set_tracer_provider.assert_called_once()
            args, _ = mock_set_tracer_provider.call_args
            assert isinstance(args[0], MockTracerProvider)
        
        # Verify LoggingInstrumentor called
        mock_instrumentor.return_value.instrument.assert_called_once_with(set_logging_formatter=False)

        # Check dictConfig called
        mock_dict_config.assert_called_once()
        
        config_args = mock_dict_config.call_args[0][0]
        assert config_args["version"] == 1
        assert "handlers" in config_args
        assert "console" in config_args["handlers"]
        assert config_args["formatters"]["json"]["()"] == jsonlogger.JsonFormatter
        
        if entity.logger_config.path:
            assert "file" in config_args["handlers"]
            assert config_args["handlers"]["file"]["filename"] == entity.logger_config.path
            assert config_args["handlers"]["file"]["formatter"] == "json"

