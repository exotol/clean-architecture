from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from app.infrastructure.observability.strategies.logging import (
    StandardLoggingStrategy,
)
from tests.schemas.unit.infrastructure.observability.strategies import (
    logging as schemas,
)


@pytest.fixture
def mock_logger() -> MagicMock:
    """Patch module _logger() so strategy uses our mock."""
    mock_log = MagicMock()
    with patch(
        "app.infrastructure.observability.strategies.logging._logger",
        return_value=mock_log,
    ):
        yield mock_log


@pytest.fixture
def mock_serializer() -> MagicMock:
    serializer = MagicMock()
    serializer.serialize.side_effect = lambda x: x
    return serializer


@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            schemas.LogStartEntity(
                event_name="TEST_EVENT",
                args=("arg1",),
                kwargs={"key": "value"},
                use_log_args=True,
            ),
            schemas.LogStartExpected(
                bind_called=True,
                args_in_bind=True,
                kwargs_in_bind=True,
                event_in_bind="TEST_EVENT",
                info_called_with="TEST_EVENT_SEND",
            ),
            id="log_start_with_args",
        ),
        pytest.param(
            schemas.LogStartEntity(
                event_name="TEST_EVENT",
                args=("arg1",),
                kwargs={"key": "value"},
                use_log_args=False,
            ),
            schemas.LogStartExpected(
                bind_called=True,
                args_in_bind=False,
                kwargs_in_bind=False,
                event_in_bind="TEST_EVENT",
                info_called_with="TEST_EVENT_SEND",
            ),
            id="log_start_without_args",
        ),
        pytest.param(
            schemas.LogStartEntity(
                event_name="SEARCH_EVENT",
                args=(),
                kwargs={"query": "test", "limit": 5},
                use_log_args=True,
                named_args={"query": "test", "limit": 5},
            ),
            schemas.LogStartExpected(
                bind_called=True,
                args_in_bind=False,
                kwargs_in_bind=False,
                event_in_bind="SEARCH_EVENT",
                info_called_with="SEARCH_EVENT_SEND",
                named_keys=["query", "limit"],
            ),
            id="log_start_with_named_args",
        ),
    ],
)
def test_log_start(
    mock_logger: MagicMock,
    mock_serializer: MagicMock,
    entity: schemas.LogStartEntity,
    expected: schemas.LogStartExpected,
) -> None:
    # Arrange
    strategy = StandardLoggingStrategy(serializer=mock_serializer)

    # Act
    context = strategy.log_start(
        entity.event_name,
        entity.args,
        entity.kwargs,
        use_log_args=entity.use_log_args,
        named_args=entity.named_args,
    )

    # Assert: return value is context dict with event
    assert isinstance(context, dict), (
        f"log_start must return a dict, got {type(context)}"
    )
    assert context["event"] == entity.event_name, (
        f"context['event'] must be {entity.event_name!r}, "
        f"got {context.get('event')!r}"
    )
    assert ("args" in context) == expected.args_in_bind, (
        f"context must have 'args' when use_log_args=True and no named_args, "
        f"expected args_in_bind={expected.args_in_bind}, got 'args' in context"
    )
    assert ("kwargs" in context) == expected.kwargs_in_bind, (
        f"context must have 'kwargs' when use_log_args=True "
        f"and no named_args, expected kwargs_in_bind="
        f"{expected.kwargs_in_bind}"
    )
    if expected.named_keys:
        for key in expected.named_keys:
            assert key in context, (
                f"context must have named key {key!r}, got {list(context)}"
            )
        assert "args" not in context, (
            "when named_args is used, context must not have key 'args'"
        )
        assert "kwargs" not in context, (
            "when named_args is used, context must not have key 'kwargs'"
        )

    # Assert: structlog logger called with event message and log_kw
    assert mock_logger.info.call_count == 1, (
        f"info must be called once, got {mock_logger.info.call_count}"
    )
    call_args = mock_logger.info.call_args
    actual_message = call_args[0][0]
    assert actual_message == expected.info_called_with, (
        f"info first arg must be {expected.info_called_with!r}, "
        f"got {actual_message!r}"
    )
    log_kw = {k: v for k, v in context.items() if k != "event"}
    for key, value in log_kw.items():
        assert call_args[1].get(key) == value, (
            f"info kwargs[{key!r}] must be {value!r}, "
            f"got {call_args[1].get(key)!r}"
        )


@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            schemas.LogSuccessEntity(
                event_name="TEST_EVENT",
                result={"data": "test"},
                use_log_result=True,
            ),
            schemas.LogSuccessExpected(
                bind_called=True,
                result_in_bind=True,
                info_called_with="TEST_EVENT_SUCCESS",
            ),
            id="log_success_with_result",
        ),
        pytest.param(
            schemas.LogSuccessEntity(
                event_name="TEST_EVENT",
                result={"data": "test"},
                use_log_result=False,
            ),
            schemas.LogSuccessExpected(
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
    entity: schemas.LogSuccessEntity,
    expected: schemas.LogSuccessExpected,
) -> None:
    # Arrange
    strategy = StandardLoggingStrategy(serializer=mock_serializer)
    context = {"event": entity.event_name}

    # Act
    strategy.log_success(
        entity.event_name,
        entity.result,
        context,
        use_log_result=entity.use_log_result,
    )

    # Assert: info called once with correct event message
    assert mock_logger.info.call_count == 1, (
        f"info must be called once, got {mock_logger.info.call_count}"
    )
    call_args = mock_logger.info.call_args
    actual_message = call_args[0][0]
    assert actual_message == expected.info_called_with, (
        f"info first arg must be {expected.info_called_with!r}, "
        f"got {actual_message!r}"
    )
    assert ("result" in call_args[1]) == expected.result_in_bind, (
        f"info kwargs must contain 'result' when use_log_result=True, "
        f"expected result_in_bind={expected.result_in_bind}, "
        f"got 'result' in kwargs = {'result' in call_args[1]}"
    )


@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            schemas.LogErrorEntity(
                event_name="TEST_EVENT",
                exc=ValueError("test error"),
            ),
            schemas.LogErrorExpected(
                event_message="TEST_EVENT_ERROR",
                exc_info_is_exc=True,
            ),
            id="log_error",
        ),
    ],
)
def test_log_error(
    mock_logger: MagicMock,
    mock_serializer: MagicMock,
    entity: schemas.LogErrorEntity,
    expected: schemas.LogErrorExpected,
) -> None:
    # Arrange
    strategy = StandardLoggingStrategy(serializer=mock_serializer)
    context = {"event": entity.event_name}

    # Act
    strategy.log_error(entity.event_name, entity.exc, context)

    # Assert: error called once with event message and exc_info
    assert mock_logger.error.call_count == 1, (
        f"error must be called once, got {mock_logger.error.call_count}"
    )
    call_args = mock_logger.error.call_args
    actual_message = call_args[0][0]
    assert actual_message == expected.event_message, (
        f"error first arg must be {expected.event_message!r}, "
        f"got {actual_message!r}"
    )
    assert call_args[1]["exc_info"] is entity.exc, (
        f"error kwargs['exc_info'] must be the same exc instance, "
        f"got {call_args[1].get('exc_info')}"
    )
