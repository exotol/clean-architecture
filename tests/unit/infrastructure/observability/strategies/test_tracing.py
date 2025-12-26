from unittest.mock import MagicMock, patch

import pytest

from app.infrastructure.observability.strategies.tracing import OpentelemetryTracingStrategy
from tests.schemas.unit.infrastructure.observability.strategies.tracing import (
    StartSpanEntity,
    StartSpanExpected,
)


@pytest.fixture
def mock_trace():
    with patch("app.infrastructure.observability.strategies.tracing.trace") as mock:
        yield mock

@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            StartSpanEntity(name="TEST_SPAN"),
            StartSpanExpected(
                tracer_called_with="app.infrastructure.observability.strategies.tracing",
                kind_attr="INTERNAL",
            ),
            id="start_span",
        ),
    ],
)
def test_start_span(
    mock_trace: MagicMock,
    entity: StartSpanEntity,
    expected: StartSpanExpected
):
    strategy = OpentelemetryTracingStrategy()
    
    # Verify tracer is retrieved
    mock_trace.get_tracer.assert_called_with(expected.tracer_called_with)
    
    # Test start_span
    strategy.start_span(entity.name)
    
    # Verify start_as_current_span called on tracer
    tracer = mock_trace.get_tracer.return_value
    tracer.start_as_current_span.assert_called_with(
        entity.name,
        kind=mock_trace.SpanKind.INTERNAL
    )
    
    # Assertions with descriptive messages
    assert mock_trace.get_tracer.called, (
        f"Expected trace.get_tracer to be called. "
        f"expected=True, actual={mock_trace.get_tracer.called}"
    )
    
    call_args = mock_trace.get_tracer.call_args[0]
    assert call_args[0] == expected.tracer_called_with, (
        f"Expected trace.get_tracer to be called with correct name. "
        f"expected={expected.tracer_called_with}, actual={call_args[0]}"
    )
    
    assert tracer.start_as_current_span.called, (
        f"Expected tracer.start_as_current_span to be called. "
        f"expected=True, actual={tracer.start_as_current_span.called}"
    )
    
    span_call_args = tracer.start_as_current_span.call_args
    assert span_call_args[0][0] == entity.name, (
        f"Expected span name to match. "
        f"expected={entity.name}, actual={span_call_args[0][0]}"
    )
    
    assert span_call_args[1]["kind"] == mock_trace.SpanKind.INTERNAL, (
        f"Expected span kind to be INTERNAL. "
        f"expected={mock_trace.SpanKind.INTERNAL}, actual={span_call_args[1]['kind']}"
    )

def test_end_span(mock_trace: MagicMock):
    # This test is simple enough to not need parametrization for now, 
    # as it's a no-op/pass-through.
    strategy = OpentelemetryTracingStrategy()
    span = MagicMock()
    strategy.end_span(span)
    
    # No assertions needed for no-op, but we can assert no exception raised
    assert True, "Expected no exception to be raised"
