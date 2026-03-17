from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from app.infrastructure.observability.strategies.tracing import (
    OpentelemetryTracingStrategy,
)
from tests.schemas.unit.infrastructure.observability.strategies import (
    tracing as schemas,
)


@pytest.fixture
def mock_trace():
    with patch(
        "app.infrastructure.observability.strategies.tracing.trace",
    ) as mock:
        yield mock


@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            schemas.StartSpanEntity(name="TEST_SPAN"),
            schemas.StartSpanExpected(
                tracer_called_with="app.infrastructure.observability.strategies.tracing",
                kind_attr="INTERNAL",
            ),
            id="start_span",
        ),
    ],
)
def test_start_span(
    mock_trace: MagicMock,
    entity: schemas.StartSpanEntity,
    expected: schemas.StartSpanExpected,
):
    # Arrange
    strategy = OpentelemetryTracingStrategy()

    # Act
    strategy.start_span(entity.name)

    # Assert
    assert mock_trace.get_tracer.call_count == 1, (
        f"Expected trace.get_tracer to be called once, "
        f"got {mock_trace.get_tracer.call_count}"
    )
    actual_tracer_name = mock_trace.get_tracer.call_args[0][0]
    assert actual_tracer_name == expected.tracer_called_with, (
        f"Expected trace.get_tracer(name={expected.tracer_called_with!r}), "
        f"got {actual_tracer_name!r}"
    )

    tracer = mock_trace.get_tracer.return_value
    assert tracer.start_as_current_span.call_count == 1, (
        f"Expected tracer.start_as_current_span to be called once, "
        f"got {tracer.start_as_current_span.call_count}"
    )
    span_call_args = tracer.start_as_current_span.call_args
    assert span_call_args[0][0] == entity.name, (
        f"Expected span name {entity.name!r}, got {span_call_args[0][0]!r}"
    )
    actual_kind = span_call_args[1]["kind"]
    expected_kind = mock_trace.SpanKind.INTERNAL
    assert actual_kind == expected_kind, (
        f"Expected kind INTERNAL, got {actual_kind!r}"
    )


def test_end_span() -> None:
    # Arrange
    strategy = OpentelemetryTracingStrategy()
    span = MagicMock()

    # Act
    strategy.end_span(span)

    # Assert
    assert True, "Expected end_span to be a no-op without raising"
