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


def _assert_instrument_and_structlog(
    expected: LoggingExpected,
    mock_set_tracer_provider: MagicMock,
    mock_structlog_configure: MagicMock,
    mock_instrumentor: MagicMock,
) -> None:
    """Assert OTLP instrumentor and structlog.configure calls."""
    instrument = mock_instrumentor.return_value.instrument
    assert instrument.call_count == 1, (
        f"LoggingInstrumentor.instrument must be called once, "
        f"got {instrument.call_count}"
    )
    kw_inst = (
        instrument.call_args[1]
        if instrument.call_args
        and len(instrument.call_args) > 1
        and instrument.call_args[1]
        else {}
    )
    assert kw_inst.get("set_logging_formatter") is False, (
        f"instrument must be called with set_logging_formatter=False, "
        f"got {kw_inst}"
    )

    assert mock_structlog_configure.call_count == 1, (
        f"structlog.configure must be called exactly once, "
        f"got {mock_structlog_configure.call_count}"
    )
    call_kw = (
        mock_structlog_configure.call_args[1]
        if mock_structlog_configure.call_args
        and len(mock_structlog_configure.call_args) > 1
        and mock_structlog_configure.call_args[1]
        else {}
    )
    assert "processors" in call_kw, (
        f"structlog.configure call must include 'processors', "
        f"got keys = {list(call_kw.keys())}"
    )
    assert "logger_factory" in call_kw, (
        f"structlog.configure call must include 'logger_factory', "
        f"got keys = {list(call_kw.keys())}"
    )
    assert isinstance(
        call_kw["logger_factory"],
        structlog.stdlib.LoggerFactory,
    ), (
        f"logger_factory must be LoggerFactory instance, "
        f"got {type(call_kw['logger_factory'])}"
    )

    if expected.trace_provider_set:
        assert mock_set_tracer_provider.call_count == 1, (
            f"trace.set_tracer_provider must be called when OTLP enabled, "
            f"got {mock_set_tracer_provider.call_count}"
        )
        assert isinstance(
            mock_set_tracer_provider.call_args[0][0],
            _MockTracerProvider,
        ), (
            "set_tracer_provider must receive TracerProvider instance, "
            f"got {type(mock_set_tracer_provider.call_args[0][0])}"
        )


def _assert_root_handlers(
    entity: LoggingEntity,
) -> None:
    """Assert root logger has ProcessorFormatter handlers."""
    root = logging.getLogger()
    assert len(root.handlers) >= 1, (
        f"Root logger must have at least one handler, got {len(root.handlers)}"
    )
    fmt = root.handlers[0].formatter
    assert isinstance(fmt, structlog.stdlib.ProcessorFormatter), (
        f"Console handler formatter must be ProcessorFormatter, "
        f"got {type(fmt)}"
    )
    if entity.logger_config.path:
        assert len(root.handlers) >= 2, (
            f"When path is set, root must have file handler, "
            f"got {len(root.handlers)} handlers"
        )
        assert root.handlers[1].formatter is fmt, (
            "File handler must use same ProcessorFormatter as console"
        )


@pytest.fixture
def mock_trace_provider() -> MagicMock:
    with patch(
        "app.infrastructure.observability.logging.trace.get_tracer_provider",
    ) as mock:
        yield mock


@pytest.fixture
def mock_set_tracer_provider() -> MagicMock:
    with patch(
        "app.infrastructure.observability.logging.trace.set_tracer_provider",
    ) as mock:
        yield mock


@pytest.fixture
def mock_structlog_configure() -> MagicMock:
    with patch(
        "app.infrastructure.observability.logging.structlog.configure",
    ) as mock:
        yield mock


@pytest.fixture
def mock_instrumentor() -> MagicMock:
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
        pytest.param(
            LoggingEntity(
                logger_config=LoggerConfig(
                    level=LogLevel.INFO,
                    format="%(message)s",
                    path=None,
                    rotation="10 MB",
                    retention="10 days",
                    loggers_to_root=[],
                    log_format="text",
                    mute_loggers=["httpx", "httpcore"],
                ),
                otlp_config=OTLPConfig(
                    enabled=False,
                    endpoint="",
                    service_name="test",
                    insecure=False,
                ),
            ),
            LoggingExpected(),
            id="success_text_format_with_muted_loggers",
        ),
    ],
)
def test_setup_logging(
    entity: LoggingEntity,
    expected: LoggingExpected,
    logging_mocks: tuple[MagicMock, MagicMock, MagicMock, MagicMock],
    tmp_path: Any,
) -> None:
    # Arrange
    (
        mock_trace_provider,
        mock_set_tracer_provider,
        mock_structlog_configure,
        mock_instrumentor,
    ) = logging_mocks
    mock_trace_provider.return_value = None
    if entity.logger_config.path:
        entity.logger_config.path = str(tmp_path / "logs.json")

    # Act
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
        setup_logging(entity.logger_config, entity.otlp_config)

        # Assert
        _assert_instrument_and_structlog(
            expected,
            mock_set_tracer_provider,
            mock_structlog_configure,
            mock_instrumentor,
        )
        _assert_root_handlers(entity)
