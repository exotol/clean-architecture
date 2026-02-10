from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from opentelemetry import trace

from app.infrastructure.observability.logging import setup_logging
from app.utils.configs import LoggerConfig
from app.utils.configs import LogLevel
from app.utils.configs import OTLPConfig
from tests.schemas.unit.infrastructure.logging import LoggingEntity
from tests.schemas.unit.infrastructure.logging import LoggingExpected


@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            LoggingEntity(
                logger_config=LoggerConfig(
                    level=LogLevel.INFO,
                    format="json",
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
                    format="console",
                    path="/tmp/logs",
                    rotation="1 day",
                    retention="1 week",
                    loggers_to_root=["uvicorn"],
                ),
                otlp_config=OTLPConfig(
                    enabled=True,
                    endpoint="console",  # Local endpoint
                    service_name="test-service",
                    insecure=True,
                ),
            ),
            LoggingExpected(),
            id="success_file_logger_with_local_otlp",
        ),
        pytest.param(
            LoggingEntity(
                logger_config=LoggerConfig(
                    level=LogLevel.INFO,
                    format="json",
                    path=None,
                    rotation="10 MB",
                    retention="10 days",
                    loggers_to_root=[],
                ),
                otlp_config=OTLPConfig(
                    enabled=True,
                    endpoint="http://otel-collector",
                    service_name="test-service",
                    insecure=True,
                ),
            ),
            LoggingExpected(),
            id="success_remote_otlp",
        ),
    ],
)
def test_setup_logging(
    entity: LoggingEntity,
    expected: LoggingExpected,
) -> None:
    # Arrange
    # Create dummy classes to bypass isinstance checks
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

    with patch("app.infrastructure.observability.logging.logger") as mock_logger, \
         patch("app.infrastructure.observability.logging.trace") as mock_trace, \
         patch("app.infrastructure.observability.logging.TracerProvider", new=MockTracerProvider), \
         patch("app.infrastructure.observability.logging.BatchSpanProcessor", new=MockBatchSpanProcessor), \
         patch("app.infrastructure.observability.logging.OTLPSpanExporter", new=MockOTLPSpanExporter), \
         patch("app.infrastructure.observability.logging.ConsoleSpanExporter", new=MockConsoleSpanExporter), \
         patch("app.infrastructure.observability.logging.Resource", new=MockResource):

        # Prepare trace mock to return explicit None, so isinstance(None, MockTracerProvider) is False
        mock_trace.get_tracer_provider.return_value = None
        
        # We need to spy on the library trace.set_tracer_provider to verify it was called
        # mock_trace is already a MagicMock, so we can check it directly

        # Act
        setup_logging(entity.logger_config, entity.otlp_config)

        # Assert
        if expected.trace_provider_set:
            mock_trace.set_tracer_provider.assert_called_once()
            # Assert that the argument passed is an instance of our MockTracerProvider
            args, _ = mock_trace.set_tracer_provider.call_args
            assert isinstance(args[0], MockTracerProvider)
        
        if expected.logger_removed:
            mock_logger.remove.assert_called_once()
            
        if expected.logger_configured:
            mock_logger.configure.assert_called_once()
            # Verify add is called at least once (for stdout)
            assert mock_logger.add.call_count >= 1


def test_record_patcher() -> None:
    # Arrange
    from app.infrastructure.observability.logging import record_patcher
    
    mock_record = MagicMock(spec=dict)
    mock_record.__getitem__.side_effect = lambda k: {} if k == "extra" else None
    
    with patch("app.infrastructure.observability.logging.trace.get_current_span") as mock_get_span:
        mock_span = MagicMock()
        mock_context = MagicMock()
        mock_context.is_valid = True
        mock_context.trace_id = 12345678901234567890123456789012
        mock_context.span_id = 1234567890123456
        
        mock_span.get_span_context.return_value = mock_context
        mock_get_span.return_value = mock_span
        
        # Act
        record_patcher(mock_record)
        
        # Assert
        # Check that extra dict was modified
        # Since we mocked __getitem__ to return a new dict each time for 'extra', we can't easily check it
        # Let's use a real dict for the record to be safer
        
        record = {"extra": {}}
        record_patcher(record)
        
        assert "trace_id" in record["extra"]
        assert "span_id" in record["extra"]
        assert record["extra"]["trace_id"] == format(12345678901234567890123456789012, "032x")


@patch("app.infrastructure.observability.logging.logger")
def test_intercept_handler_emit(mock_logger):
    from app.infrastructure.observability.logging import InterceptHandler
    import logging
    
    # Configure logger.level to return an object with .name
    mock_level = MagicMock()
    mock_level.name = "INFO"
    mock_logger.level.return_value = mock_level
    
    handler = InterceptHandler()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="test message",
        args=(),
        exc_info=None
    )
    
    handler.emit(record)
    mock_logger.opt.assert_called()
    mock_logger.opt.return_value.log.assert_called_with("INFO", "test message")


def test_setup_logging_with_file_output() -> None:
    # Manual setup config to avoid fixture dependencies if not needed or reuse
    from app.utils.configs import LoggerConfig, OTLPConfig, LogLevel
    
    logger_config = LoggerConfig(
        level=LogLevel.INFO,
        format="json",
        path="/tmp/test.log",  # Path is set
        rotation="10 MB",
        retention="10 days",
        loggers_to_root=[],
    )
    otlp_config = OTLPConfig(
        enabled=False, 
        endpoint="", 
        service_name="test",
        insecure=True, # Added required field
    )
    
    with patch("app.infrastructure.observability.logging.logger") as mock_logger, \
         patch("app.infrastructure.observability.logging.logging") as mock_logging, \
         patch("app.infrastructure.observability.logging.trace"):
        
        setup_logging(logger_config, otlp_config)
        
        # Verify logger.add called for file
        # logger.add is called twice: once for stdout, once for file
        assert mock_logger.add.call_count == 2
        
        # Check arguments for the file call
        calls = mock_logger.add.call_args_list
        # We look for a call where args[0] is the path
        path_call = any(c[0][0] == "/tmp/test.log" for c in calls)
        assert path_call


@patch("app.infrastructure.observability.logging.logger")
def test_intercept_handler_invalid_level(mock_logger):
    from app.infrastructure.observability.logging import InterceptHandler
    import logging
    
    # Configure logger.level to raise ValueError
    mock_logger.level.side_effect = ValueError
    
    handler = InterceptHandler()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="test message",
        args=(),
        exc_info=None
    )
    
    handler.emit(record)
    # Should use level number
    mock_logger.opt.return_value.log.assert_called_with(logging.INFO, "test message")


def test_record_patcher_no_span() -> None:
    from app.infrastructure.observability.logging import record_patcher
    
    with patch("app.infrastructure.observability.logging.trace.get_current_span") as mock_get_span:
        mock_get_span.return_value = None
        
        record = {}
        record_patcher(record)
        
        # Should return early, record not modified (except potentially if side effects exist, but logic says return)
        assert record == {}


def test_intercept_handler_stack() -> None:
    from app.infrastructure.observability.logging import InterceptHandler
    import logging
    
    # We need to trace the call from logging module to handler to trigger the while loop
    # frame.f_code.co_filename == logging.__file__
    
    handler = InterceptHandler()
    logger = logging.getLogger("stack_test")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    with patch("app.infrastructure.observability.logging.logger") as mock_loguru:
        logger.info("Test stack")
        
        # Verify loguru was called
        mock_loguru.opt.assert_called()
        # Check depth argument
        # We can't easily assert exact depth but we can assert it was called
        args, kwargs = mock_loguru.opt.call_args
        assert "depth" in kwargs
        assert kwargs["depth"] >= 2
