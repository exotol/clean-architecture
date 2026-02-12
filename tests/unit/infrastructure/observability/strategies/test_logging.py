from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from app.infrastructure.observability.strategies.logging import StandardLoggingStrategy
from tests.schemas.unit.infrastructure.observability.strategies.logging import (
    LogErrorEntity,
    LogErrorExpected,
    LogStartEntity,
    LogStartExpected,
    LogSuccessEntity,
    LogSuccessExpected,
)


@pytest.fixture
def mock_logger():
    # Patch the logger in the module
    with patch(
        "app.infrastructure.observability.strategies.logging.logger"
    ) as mock:
        yield mock


@pytest.fixture
def mock_serializer() -> MagicMock:
    serializer = MagicMock()
    serializer.serialize.side_effect = lambda x: x  # Pass-through
    return serializer


@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            LogStartEntity(
                event_name="TEST_EVENT",
                args=("arg1",),
                kwargs={"key": "value"},
                use_log_args=True,
            ),
            LogStartExpected(
                bind_called=True, # In new strat, this means extra context is built
                args_in_bind=True,
                kwargs_in_bind=True,
                event_in_bind="TEST_EVENT",
                info_called_with="TEST_EVENT_SEND",
            ),
            id="log_start_with_args",
        ),
        pytest.param(
            LogStartEntity(
                event_name="TEST_EVENT",
                args=("arg1",),
                kwargs={"key": "value"},
                use_log_args=False,
            ),
            LogStartExpected(
                bind_called=True,
                args_in_bind=False,
                kwargs_in_bind=False,
                event_in_bind="TEST_EVENT",
                info_called_with="TEST_EVENT_SEND",
            ),
            id="log_start_without_args",
        ),
    ],
)
def test_log_start(
    mock_logger: MagicMock,
    mock_serializer: MagicMock,
    entity: LogStartEntity,
    expected: LogStartExpected,
) -> None:
    strategy = StandardLoggingStrategy(serializer=mock_serializer)

    context = strategy.log_start(
        entity.event_name,
        entity.args,
        entity.kwargs,
        use_log_args=entity.use_log_args,
    )

    # Verify return value IS the context dict
    assert isinstance(context, dict)
    assert context["event"] == entity.event_name
    
    if expected.args_in_bind:
        assert "args" in context
    else:
        assert "args" not in context
        
    if expected.kwargs_in_bind:
        assert "kwargs" in context
    else:
        assert "kwargs" not in context

    # Verify logger called with extra=context
    mock_logger.info.assert_called_with(expected.info_called_with, extra=context)


@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            LogSuccessEntity(
                event_name="TEST_EVENT",
                result={"data": "test"},
                use_log_result=True,
            ),
            LogSuccessExpected(
                bind_called=True,
                result_in_bind=True,
                info_called_with="TEST_EVENT_SUCCESS",
            ),
            id="log_success_with_result",
        ),
        pytest.param(
            LogSuccessEntity(
                event_name="TEST_EVENT",
                result={"data": "test"},
                use_log_result=False,
            ),
            LogSuccessExpected(
                bind_called=False,
                result_in_bind=False,
                info_called_with="TEST_EVENT_SUCCESS",
            ),
            id="log_success_without_result",
        ),
    ],
)
def test_log_success(
    mock_logger: MagicMock,
    mock_serializer: MagicMock,
    entity: LogSuccessEntity,
    expected: LogSuccessExpected,
) -> None:
    strategy = StandardLoggingStrategy(serializer=mock_serializer)
    
    # Simulate context passed from log_start
    context = {"event": entity.event_name}

    strategy.log_success(
        entity.event_name,
        entity.result,
        context,
        use_log_result=entity.use_log_result,
    )

    # We expect logger.info to be called with extra=new_context
    # Check if we modified context in place or created new one?
    # Implementation created new context if adding result? No, it used passed context.
    # Actually implementation checked if context is dict.
    
    if expected.result_in_bind:
        assert "result" in context
    else:
        # If we didn't add result, maybe it's not in context
        assert "result" not in context

    mock_logger.info.assert_called_with(expected.info_called_with, extra=context)


@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            LogErrorEntity(
                event_name="TEST_EVENT",
                exc=ValueError("test error"),
            ),
            LogErrorExpected(
                exception_called_with="TEST_EVENT_ERROR",
            ),
            id="log_error",
        ),
    ],
)
def test_log_error(
    mock_logger: MagicMock,
    mock_serializer: MagicMock,
    entity: LogErrorEntity,
    expected: LogErrorExpected,
) -> None:
    strategy = StandardLoggingStrategy(serializer=mock_serializer)
    context = {"event": entity.event_name}

    strategy.log_error(entity.event_name, entity.exc, context)

    mock_logger.error.assert_called_with(
        expected.exception_called_with, exc_info=entity.exc, extra=context
    )
