from __future__ import annotations

import logging
from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
import structlog

from app.infrastructure.observability.logging import setup_logging
from app.utils.configs import LoggerConfig
from app.utils.configs import LogLevel
from app.utils.configs import OTLPConfig
from tests.schemas.unit.infrastructure.logging import LoggingEntity
from tests.schemas.unit.infrastructure.logging import LoggingExpected


def _assert_logging_config(
    mock_structlog_configure: MagicMock,
    mock_set_tracer_provider: MagicMock,
    mock_instrumentor: MagicMock,
    expected: LoggingExpected,
    mock_tracer_provider_instance: Any,
) -> None:
    """Assert logging setup results (structlog + stdlib, no dictConfig)."""
    if expected.trace_provider_set:
        mock_set_tracer_provider.assert_called_once()
        args, _ = mock_set_tracer_provider.call_args
        assert isinstance(args[0], type(mock_tracer_provider_instance))
    mock_instrumentor.return_value.instrument.assert_called_once_with(
        set_logging_formatter=False,
    )
    mock_structlog_configure.assert_called_once()
    call_kw = mock_structlog_configure.call_args[1]
    assert "processors" in call_kw
    assert "logger_factory" in call_kw
    assert isinstance(
        call_kw["logger_factory"],
        structlog.stdlib.LoggerFactory,
    )


def _assert_root_handlers(
    entity: LoggingEntity,
) -> None:
    """Assert root logger has console handler with ProcessorFormatter."""
    root = logging.getLogger()
    assert len(root.handlers) >= 1
    console_formatter = root.handlers[0].formatter
    assert isinstance(
        console_formatter,
        structlog.stdlib.ProcessorFormatter,
    )
    if entity.logger_config.path:
        assert len(root.handlers) >= 2
        assert root.handlers[1].formatter is console_formatter


class _MockTracerProvider:
    def __init__(self, resource: Any = None) -> None:
        pass

    def add_span_processor(self, processor: Any) -> None:
        pass


class _MockBatchSpanProcessor:
    def __init__(self, exporter: Any) -> None:
        pass


class _MockOTLPSpanExporter:
    def __init__(self, endpoint: Any = None, insecure: Any = None) -> None:
        pass


class _MockConsoleSpanExporter:
    def __init__(self) -> None:
        pass


class _MockResource:
    @staticmethod
    def create(*, attributes: Any) -> MagicMock:
        return MagicMock(attributes=attributes)


@pytest.fixture
def mock_trace_provider():
    with patch(
        "app.infrastructure.observability.logging.trace.get_tracer_provider",
    ) as mock:
        yield mock


@pytest.fixture
def mock_set_tracer_provider():
    with patch(
        "app.infrastructure.observability.logging.trace.set_tracer_provider",
    ) as mock:
        yield mock


@pytest.fixture
def mock_structlog_configure():
    with patch(
        "app.infrastructure.observability.logging.structlog.configure",
    ) as mock:
        yield mock


@pytest.fixture
def mock_instrumentor():
    with patch(
        "app.infrastructure.observability.logging.LoggingInstrumentor",
    ) as mock:
        yield mock


@pytest.fixture
def logging_mocks(
    mock_trace_provider: MagicMock,
    mock_set_tracer_provider: MagicMock,
    mock_structlog_configure: MagicMock,
    mock_instrumentor: MagicMock,
) -> tuple[MagicMock, MagicMock, MagicMock, MagicMock]:
    """Single fixture combining all logging mocks (reduces test arity)."""
    return (
        mock_trace_provider,
        mock_set_tracer_provider,
        mock_structlog_configure,
        mock_instrumentor,
    )


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
                    path="logs.json",
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
    logging_mocks: tuple[MagicMock, MagicMock, MagicMock, MagicMock],
    tmp_path: Any,
) -> None:
    """Test setup_logging configures OpenTelemetry and structlog+stdlib."""
    (
        mock_trace_provider,
        mock_set_tracer_provider,
        mock_structlog_configure,
        mock_instrumentor,
    ) = logging_mocks
    mock_trace_provider.return_value = None

    with (
        patch(
            "app.infrastructure.observability.logging.TracerProvider",
            new=_MockTracerProvider,
        ),
        patch(
            "app.infrastructure.observability.logging.BatchSpanProcessor",
            new=_MockBatchSpanProcessor,
        ),
        patch(
            "app.infrastructure.observability.logging.OTLPSpanExporter",
            new=_MockOTLPSpanExporter,
        ),
        patch(
            "app.infrastructure.observability.logging.ConsoleSpanExporter",
            new=_MockConsoleSpanExporter,
        ),
        patch(
            "app.infrastructure.observability.logging.Resource",
            new=_MockResource,
        ),
    ):
        if entity.logger_config.path:
            entity.logger_config.path = str(tmp_path / "logs.json")
        setup_logging(entity.logger_config, entity.otlp_config)

        _assert_logging_config(
            mock_structlog_configure,
            mock_set_tracer_provider,
            mock_instrumentor,
            expected,
            _MockTracerProvider(None),
        )

        _assert_root_handlers(entity)
