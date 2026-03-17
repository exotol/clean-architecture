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
    # Arrange

    # Act
    OpentelemetryMetricsStrategy()

    # Assert
    assert mock_metrics.get_meter.called, (
        "Expected metrics.get_meter to be called on init"
    )
    call_args = mock_metrics.get_meter.call_args[0]
    expected_meter_name = "app.infrastructure.observability.strategies.metrics"
    assert call_args[0] == expected_meter_name, (
        f"Expected get_meter({expected_meter_name!r}), got {call_args[0]!r}"
    )

    meter = mock_metrics.get_meter.return_value
    assert meter.create_counter.called, (
        "Expected meter.create_counter to be called"
    )
    first_counter_kw = meter.create_counter.call_args_list[0][1]
    assert first_counter_kw["name"] == constants.METRICS_REQUESTS_TOTAL_NAME, (
        f"Expected counter name {constants.METRICS_REQUESTS_TOTAL_NAME!r}, "
        f"got {first_counter_kw['name']!r}"
    )

    assert meter.create_histogram.called, (
        "Expected meter.create_histogram to be called"
    )
    first_histogram_kw = meter.create_histogram.call_args_list[0][1]
    assert (
        first_histogram_kw["name"] == constants.METRICS_REQUEST_DURATION_NAME
    ), (
        f"Expected histogram name "
        f"{constants.METRICS_REQUEST_DURATION_NAME!r}, "
        f"got {first_histogram_kw['name']!r}"
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
    # Arrange
    strategy = OpentelemetryMetricsStrategy()
    strategy.requests_total = MagicMock()
    strategy.request_duration = MagicMock()

    # Act
    strategy.record_request(
        event_name=entity.event_name,
        duration=entity.duration,
        status=entity.status,
        error_type=entity.error_type,
    )

    # Assert
    assert strategy.requests_total.add.called, (
        "Expected requests_total.add to be called"
    )
    counter_args = strategy.requests_total.add.call_args
    assert counter_args[0][0] == expected.counter_add_value, (
        f"Expected counter add value {expected.counter_add_value}, "
        f"got {counter_args[0][0]}"
    )
    assert counter_args[0][1] == expected.counter_attrs, (
        f"Expected counter attrs {expected.counter_attrs}, "
        f"got {counter_args[0][1]}"
    )

    assert strategy.request_duration.record.called, (
        "Expected request_duration.record to be called"
    )
    histogram_args = strategy.request_duration.record.call_args
    assert histogram_args[0][0] == expected.histogram_record_value, (
        f"Expected histogram value {expected.histogram_record_value}, "
        f"got {histogram_args[0][0]}"
    )
    assert histogram_args[0][1] == expected.histogram_attrs, (
        f"Expected histogram attrs {expected.histogram_attrs}, "
        f"got {histogram_args[0][1]}"
    )


def test_record_sla() -> None:
    # Arrange
    strategy = OpentelemetryMetricsStrategy()
    strategy.sla_requests_total = MagicMock()
    strategy.sla_latency = MagicMock()

    # Act
    strategy.record_sla(
        event_name="test_sla",
        duration=0.5,
        success=True,
    )

    # Assert
    assert strategy.sla_requests_total.add.call_count == 1, (
        f"Expected sla_requests_total.add called once, "
        f"got {strategy.sla_requests_total.add.call_count}"
    )
    assert strategy.sla_requests_total.add.call_args[0] == (
        1,
        {"event": "test_sla", "status": "success"},
    ), (
        f"Expected add(1, {{'event': 'test_sla', 'status': 'success'}}), "
        f"got {strategy.sla_requests_total.add.call_args}"
    )
    assert strategy.sla_latency.record.call_count == 1, (
        f"Expected sla_latency.record called once, "
        f"got {strategy.sla_latency.record.call_count}"
    )
    assert strategy.sla_latency.record.call_args[0] == (
        0.5,
        {"event": "test_sla"},
    ), (
        f"Expected record(0.5, {{'event': 'test_sla'}}), "
        f"got {strategy.sla_latency.record.call_args}"
    )

    strategy.sla_requests_total.reset_mock()
    strategy.sla_latency.reset_mock()
    strategy.record_sla(
        event_name="test_sla_fail",
        duration=0.1,
        success=False,
    )
    assert strategy.sla_requests_total.add.call_count == 1, (
        f"Expected sla_requests_total.add called once (fail path), "
        f"got {strategy.sla_requests_total.add.call_count}"
    )
    assert strategy.sla_requests_total.add.call_args[0] == (
        1,
        {"event": "test_sla_fail", "status": "error"},
    ), (
        f"Expected add(1, {{'event': 'test_sla_fail', 'status': 'error'}}), "
        f"got {strategy.sla_requests_total.add.call_args}"
    )
