from __future__ import annotations

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from app.core import constants
from app.infrastructure.observability.strategies.metrics import (
    OpentelemetryMetricsStrategy,
)
from tests.schemas.unit.infrastructure.observability.strategies import (
    metrics as schemas,
)


@pytest.fixture
def mock_metrics() -> MagicMock:
    with patch(
        "app.infrastructure.observability.strategies.metrics.metrics",
    ) as mock:
        yield mock


def test_init(mock_metrics: MagicMock) -> None:
    OpentelemetryMetricsStrategy()

    assert mock_metrics.get_meter.called

    call_args = mock_metrics.get_meter.call_args[0]
    expected_meter_name = "app.infrastructure.observability.strategies.metrics"
    assert call_args[0] == expected_meter_name

    meter = mock_metrics.get_meter.return_value

    assert meter.create_counter.called

    counter_call_kwargs = meter.create_counter.call_args[1]
    assert counter_call_kwargs["name"] == constants.METRICS_REQUESTS_TOTAL_NAME

    assert meter.create_histogram.called

    histogram_call_kwargs = meter.create_histogram.call_args[1]
    assert (
        histogram_call_kwargs["name"]
        == constants.METRICS_REQUEST_DURATION_NAME
    )


@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            schemas.RecordRequestEntity(
                event_name="TEST_EVENT",
                duration=0.123,
                status="success",
                error_type=None,
            ),
            schemas.RecordRequestExpected(
                counter_add_value=1,
                counter_attrs={"event": "TEST_EVENT", "status": "success"},
                histogram_record_value=0.123,
                histogram_attrs={"event": "TEST_EVENT"},
            ),
            id="record_success",
        ),
        pytest.param(
            schemas.RecordRequestEntity(
                event_name="TEST_EVENT",
                duration=0.456,
                status="error",
                error_type="business",
            ),
            schemas.RecordRequestExpected(
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
    entity: schemas.RecordRequestEntity,
    expected: schemas.RecordRequestExpected,
) -> None:
    strategy = OpentelemetryMetricsStrategy()

    # Mock instruments
    strategy.requests_total = MagicMock()
    strategy.request_duration = MagicMock()

    # Test record_request
    strategy.record_request(
        event_name=entity.event_name,
        duration=entity.duration,
        status=entity.status,
        error_type=entity.error_type,
    )

    # Verify counter add
    assert strategy.requests_total.add.called

    counter_args = strategy.requests_total.add.call_args
    assert counter_args[0][0] == expected.counter_add_value

    assert counter_args[0][1] == expected.counter_attrs

    # Verify histogram record
    assert strategy.request_duration.record.called

    histogram_args = strategy.request_duration.record.call_args
    assert histogram_args[0][0] == expected.histogram_record_value

    assert histogram_args[0][1] == expected.histogram_attrs
