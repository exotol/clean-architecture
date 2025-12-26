from unittest.mock import MagicMock, patch

import pytest

from app.core import constants
from app.infrastructure.observability.strategies.metrics import OpentelemetryMetricsStrategy
from tests.schemas.unit.infrastructure.observability.strategies.metrics import (
    RecordRequestEntity,
    RecordRequestExpected,
)


@pytest.fixture
def mock_metrics():
    with patch("app.infrastructure.observability.strategies.metrics.metrics") as mock:
        yield mock

def test_init(mock_metrics):
    # Init test is structural, maybe less benefit from parametrization unless we test different configs
    strategy = OpentelemetryMetricsStrategy()
    
    assert mock_metrics.get_meter.called, (
        f"Expected metrics.get_meter to be called. "
        f"expected=True, actual={mock_metrics.get_meter.called}"
    )
    
    call_args = mock_metrics.get_meter.call_args[0]
    expected_meter_name = "app.infrastructure.observability.strategies.metrics"
    assert call_args[0] == expected_meter_name, (
        f"Expected get_meter called with correct name. "
        f"expected={expected_meter_name}, actual={call_args[0]}"
    )
    
    meter = mock_metrics.get_meter.return_value
    
    assert meter.create_counter.called, (
        f"Expected meter.create_counter to be called. "
        f"expected=True, actual={meter.create_counter.called}"
    )
    
    counter_call_kwargs = meter.create_counter.call_args[1]
    assert counter_call_kwargs["name"] == constants.METRICS_REQUESTS_TOTAL_NAME, (
        f"Expected counter name to match. "
        f"expected={constants.METRICS_REQUESTS_TOTAL_NAME}, actual={counter_call_kwargs['name']}"
    )
    
    assert meter.create_histogram.called, (
        f"Expected meter.create_histogram to be called. "
        f"expected=True, actual={meter.create_histogram.called}"
    )
    
    histogram_call_kwargs = meter.create_histogram.call_args[1]
    assert histogram_call_kwargs["name"] == constants.METRICS_REQUEST_DURATION_NAME, (
        f"Expected histogram name to match. "
        f"expected={constants.METRICS_REQUEST_DURATION_NAME}, actual={histogram_call_kwargs['name']}"
    )

@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            RecordRequestEntity(
                event_name="TEST_EVENT",
                duration=0.123,
                status="success",
                error_type=None,
            ),
            RecordRequestExpected(
                counter_add_value=1,
                counter_attrs={"event": "TEST_EVENT", "status": "success"},
                histogram_record_value=0.123,
                histogram_attrs={"event": "TEST_EVENT"},
            ),
            id="record_success",
        ),
        pytest.param(
            RecordRequestEntity(
                event_name="TEST_EVENT",
                duration=0.456,
                status="error",
                error_type="business",
            ),
            RecordRequestExpected(
                counter_add_value=1,
                counter_attrs={
                    "event": "TEST_EVENT",
                    "status": "error",
                    "error_type": "business",
                },
                histogram_record_value=0.456,
                histogram_attrs={"event": "TEST_EVENT"},
            ),
            id="record_error",
        ),
    ],
)
def test_record_request(
    mock_metrics: MagicMock,
    entity: RecordRequestEntity,
    expected: RecordRequestExpected
):
    strategy = OpentelemetryMetricsStrategy()
    
    # Mock instruments
    strategy.requests_total = MagicMock()
    strategy.request_duration = MagicMock()
    
    # Test record_request
    strategy.record_request(
        event_name=entity.event_name,
        duration=entity.duration,
        status=entity.status,
        error_type=entity.error_type
    )
    
    # Verify counter add
    assert strategy.requests_total.add.called, (
        f"Expected requests_total.add to be called. "
        f"expected=True, actual={strategy.requests_total.add.called}"
    )
    
    counter_args = strategy.requests_total.add.call_args
    assert counter_args[0][0] == expected.counter_add_value, (
        f"Expected counter add value to match. "
        f"expected={expected.counter_add_value}, actual={counter_args[0][0]}"
    )
    
    assert counter_args[0][1] == expected.counter_attrs, (
        f"Expected counter attributes to match. "
        f"expected={expected.counter_attrs}, actual={counter_args[0][1]}"
    )
    
    # Verify histogram record
    assert strategy.request_duration.record.called, (
        f"Expected request_duration.record to be called. "
        f"expected=True, actual={strategy.request_duration.record.called}"
    )
    
    histogram_args = strategy.request_duration.record.call_args
    assert histogram_args[0][0] == expected.histogram_record_value, (
        f"Expected histogram record value to match. "
        f"expected={expected.histogram_record_value}, actual={histogram_args[0][0]}"
    )
    
    assert histogram_args[0][1] == expected.histogram_attrs, (
        f"Expected histogram attributes to match. "
        f"expected={expected.histogram_attrs}, actual={histogram_args[0][1]}"
    )
