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
    with patch(
        "app.infrastructure.observability.strategies.logging.loguru_logger"
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
                bind_called=True,
                args_in_bind=True,
                kwargs_in_bind=True,
                event_in_bind="TEST_EVENT",
                info_called_with="{}_SEND",
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
                info_called_with="{}_SEND",
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

    strategy.log_start(
        entity.event_name,
        entity.args,
        entity.kwargs,
        use_log_args=entity.use_log_args,
    )

    if expected.bind_called:
        assert mock_logger.bind.called, (
            f"Expected logger.bind to be called, but it was not. "
            f"expected={expected.bind_called}, actual={mock_logger.bind.called}"
        )

        call_kwargs = mock_logger.bind.call_args[1]

        assert call_kwargs["event"] == expected.event_in_bind, (
            f"Expected event in bind context to match. "
            f"expected={expected.event_in_bind}, actual={call_kwargs.get('event')}"
        )

        if expected.args_in_bind:
            assert "args" in call_kwargs, (
                f"Expected 'args' in bind context. "
                f"expected=True, actual={'args' in call_kwargs}"
            )
        else:
            assert "args" not in call_kwargs, (
                f"Expected 'args' NOT in bind context. "
                f"expected=False, actual={'args' in call_kwargs}"
            )

        if expected.kwargs_in_bind:
            assert "kwargs" in call_kwargs, (
                f"Expected 'kwargs' in bind context. "
                f"expected=True, actual={'kwargs' in call_kwargs}"
            )
        else:
            assert "kwargs" not in call_kwargs, (
                f"Expected 'kwargs' NOT in bind context. "
                f"expected=False, actual={'kwargs' in call_kwargs}"
            )

        mock_logger.bind.return_value.info.assert_called_with(
            expected.info_called_with, entity.event_name
        )


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
                info_called_with="{}_SUCCESS",
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
                info_called_with="{}_SUCCESS",
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
    context = mock_logger.bind.return_value

    strategy.log_success(
        entity.event_name,
        entity.result,
        context,
        use_log_result=entity.use_log_result,
    )

    if expected.bind_called:
        assert context.bind.called, (
            f"Expected context.bind to be called. "
            f"expected={expected.bind_called}, actual={context.bind.called}"
        )

        if expected.result_in_bind:
            call_kwargs = context.bind.call_args[1]
            assert "result" in call_kwargs, (
                f"Expected 'result' in bind context. "
                f"expected=True, actual={'result' in call_kwargs}"
            )

        context.bind.return_value.info.assert_called_with(
            expected.info_called_with, entity.event_name
        )
    else:
        # If bind not called, info called directly on context
        context.info.assert_called_with(expected.info_called_with, entity.event_name)


@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            LogErrorEntity(
                event_name="TEST_EVENT",
                exc=ValueError("test error"),
            ),
            LogErrorExpected(
                exception_called_with="{}_ERROR",
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
    context = mock_logger.bind.return_value

    strategy.log_error(entity.event_name, entity.exc, context)

    context.exception.assert_called_with(
        expected.exception_called_with, entity.event_name
    )
