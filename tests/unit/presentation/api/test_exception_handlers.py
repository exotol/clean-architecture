from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch

from fastapi import Request
from fastapi import status
from fastapi.exceptions import RequestValidationError
import pytest

from app.core.constants import TRACE_ID
from app.core.exceptions import BusinessError
from app.core.exceptions import InfrastructureError
from app.core.exceptions import RateLimitExceededError
from app.core.exceptions import Reasons
from app.presentation import exception_handlers
from tests.schemas.unit.presentation.exception_handlers import (
    ExceptionHandlerEntity,
)
from tests.schemas.unit.presentation.exception_handlers import (
    ExceptionHandlerExpected,
)


def create_error(cls: type[Exception], **kwargs: Any) -> Exception:
    e = cls()
    for k, v in kwargs.items():
        setattr(e, k, v)
    return e


def _create_mock_request(entity: ExceptionHandlerEntity) -> MagicMock:
    """Create and configure a mock Request object for handler tests."""
    mock_request = MagicMock(spec=Request)
    mock_request.url.path = entity.request_url

    mock_request.state = MagicMock()
    setattr(mock_request.state, TRACE_ID, "test-trace-id")

    mock_request.app = MagicMock()
    mock_request.app.state = MagicMock(spec=[])
    for k, v in entity.app_state.items():
        setattr(mock_request.app.state, k, v)

    mock_request.headers.get.return_value = None
    return mock_request


def _assert_content_fields(
    content: dict[str, Any],
    expected: ExceptionHandlerExpected,
) -> None:
    """Assert error content fields match expected schema."""
    type_field = content.get("type", content.get("urn_type_error"))
    assert type_field == expected.content_type_error, (
        f"Test failed, actual type = {type_field!r}, "
        f"expected = {expected.content_type_error!r}"
    )
    assert content["title"] == expected.content_title, (
        f"Test failed, actual title = {content['title']!r}, "
        f"expected = {expected.content_title!r}"
    )
    assert content["reason"] == expected.content_reason, (
        f"Test failed, actual reason = {content['reason']!r}, "
        f"expected = {expected.content_reason!r}"
    )
    if expected.content_detail is not None:
        assert content.get("detail") == expected.content_detail, (
            f"Test failed, actual detail = {content.get('detail')!r}, "
            f"expected = {expected.content_detail!r}"
        )
    if expected.expected_invalid_params is not None:
        assert (
            content.get("invalid_params") == expected.expected_invalid_params
        ), (
            f"Test failed, invalid_params = "
            f"{content.get('invalid_params')!r}, "
            f"expected = {expected.expected_invalid_params!r}"
        )


def _assert_headers_and_logs(
    response: Any,
    mock_logger: MagicMock,
    expected: ExceptionHandlerExpected,
) -> None:
    """Assert response headers and logger call counts."""
    for h_key, h_val in expected.expected_headers.items():
        actual_header = response.headers.get(h_key)
        assert actual_header == h_val, (
            f"Test failed, header {h_key} = {actual_header!r}, "
            f"expected = {h_val!r}"
        )

    if expected.log_level == "WARNING":
        assert mock_logger.warning.call_count == 1, (
            f"Expected logger.warning called once, "
            f"got {mock_logger.warning.call_count}"
        )
    elif expected.log_level == "ERROR":
        assert mock_logger.error.call_count == 1, (
            f"Expected logger.error called once, "
            f"got {mock_logger.error.call_count}"
        )


@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            ExceptionHandlerEntity(
                handler_name="business_error_handler",
                exception=create_error(
                    BusinessError,
                    title="Biz Error",
                    code="BIZ_001",
                    detail="Something happened",
                    urn_type_error="urn:biz:error",
                    status_code=status.HTTP_400_BAD_REQUEST,
                ),
            ),
            ExceptionHandlerExpected(
                status_code=status.HTTP_400_BAD_REQUEST,
                content_type_error="urn:biz:error",
                content_title="Biz Error",
                content_reason="BIZ_001",
                content_detail="Something happened",
                log_level="WARNING",
            ),
            id="business_error",
        ),
        pytest.param(
            ExceptionHandlerEntity(
                handler_name="business_error_handler",
                exception=BusinessError(
                    detail="Rule broken",
                    invalid_params=[
                        {"name": "field1", "reason": "invalid"},
                    ],
                ),
            ),
            ExceptionHandlerExpected(
                status_code=status.HTTP_400_BAD_REQUEST,
                content_type_error=(
                    Reasons.business_rule_violation.urn_type_error
                ),
                content_title=Reasons.business_rule_violation.title,
                content_reason=Reasons.business_rule_violation.code,
                content_detail="Rule broken",
                expected_invalid_params=[
                    {"name": "field1", "reason": "invalid"},
                ],
                log_level="WARNING",
            ),
            id="business_error_with_params",
        ),
        pytest.param(
            ExceptionHandlerEntity(
                handler_name="infra_error_handler",
                exception=RuntimeError("DB Connection failed"),
            ),
            ExceptionHandlerExpected(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content_type_error=Reasons.service_unavailable.urn_type_error,
                content_title=Reasons.service_unavailable.title,
                content_reason=Reasons.service_unavailable.code,
                content_detail=Reasons.service_unavailable.message,
                expected_headers={"Retry-After": "30"},
                log_level="ERROR",
            ),
            id="infra_error_runtime",
        ),
        pytest.param(
            ExceptionHandlerEntity(
                handler_name="infra_error_handler",
                exception=InfrastructureError(
                    "Redis unreachable",
                    service_name="redis",
                ),
            ),
            ExceptionHandlerExpected(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content_type_error=Reasons.service_unavailable.urn_type_error,
                content_title=Reasons.service_unavailable.title,
                content_reason=Reasons.service_unavailable.code,
                content_detail="Redis unreachable",
                expected_headers={"Retry-After": "30"},
                log_level="ERROR",
            ),
            id="infra_error_instance",
        ),
        pytest.param(
            ExceptionHandlerEntity(
                handler_name="rate_limit_error_handler",
                exception=RateLimitExceededError(),
            ),
            ExceptionHandlerExpected(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content_type_error=Reasons.rate_limit_exceeded.urn_type_error,
                content_title=Reasons.rate_limit_exceeded.title,
                content_reason=Reasons.rate_limit_exceeded.code,
                content_detail=Reasons.rate_limit_exceeded.message,
                expected_headers={"Retry-After": "60"},
                log_level="WARNING",
            ),
            id="rate_limit_error_default",
        ),
        pytest.param(
            ExceptionHandlerEntity(
                handler_name="rate_limit_error_handler",
                exception=RateLimitExceededError(
                    detail="Slow down",
                    retry_after=120.0,
                ),
            ),
            ExceptionHandlerExpected(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content_type_error=Reasons.rate_limit_exceeded.urn_type_error,
                content_title=Reasons.rate_limit_exceeded.title,
                content_reason=Reasons.rate_limit_exceeded.code,
                content_detail="Slow down",
                expected_headers={"Retry-After": "120"},
                log_level="WARNING",
            ),
            id="rate_limit_error_custom_retry",
        ),
        pytest.param(
            ExceptionHandlerEntity(
                handler_name="global_exception_handler",
                exception=ValueError("Sensitive database details"),
            ),
            ExceptionHandlerExpected(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content_type_error=(
                    Reasons.internal_server_error.urn_type_error
                ),
                content_title=Reasons.internal_server_error.title,
                content_reason=Reasons.internal_server_error.code,
                content_detail=Reasons.internal_server_error.message,
                log_level="ERROR",
            ),
            id="global_exception_hidden_details",
        ),
        pytest.param(
            ExceptionHandlerEntity(
                handler_name="global_exception_handler",
                exception=ValueError("Visible debug detail"),
                app_state={"use_exposed_details": True},
            ),
            ExceptionHandlerExpected(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content_type_error=(
                    Reasons.internal_server_error.urn_type_error
                ),
                content_title=Reasons.internal_server_error.title,
                content_reason=Reasons.internal_server_error.code,
                content_detail="Visible debug detail",
                log_level="ERROR",
            ),
            id="global_exception_exposed_details",
        ),
        pytest.param(
            ExceptionHandlerEntity(
                handler_name="request_validation_handler",
                exception=RequestValidationError(
                    [
                        {
                            "loc": ("body", "field"),
                            "msg": "field required",
                            "type": "value_error.missing",
                        },
                    ],
                ),
            ),
            ExceptionHandlerExpected(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                content_type_error=Reasons.validation_error.urn_type_error,
                content_title=Reasons.validation_error.title,
                content_reason=Reasons.validation_error.code,
                log_level="WARNING",
            ),
            id="validation_error",
        ),
    ],
)
def test_exception_handlers(
    entity: ExceptionHandlerEntity,
    expected: ExceptionHandlerExpected,
) -> None:
    # Arrange
    mock_request = _create_mock_request(entity)
    handler_func = getattr(exception_handlers, entity.handler_name)

    with patch(
        "app.presentation.exception_handlers.logger",
    ) as mock_logger:
        # Act
        response = handler_func(
            mock_request,
            entity.exception,
            **entity.handler_kwargs,
        )

        # Assert
        assert response.status_code == expected.status_code, (
            f"Test failed, actual status_code = {response.status_code}, "
            f"expected = {expected.status_code}"
        )
        content = json.loads(response.body)
        _assert_content_fields(content, expected)
        _assert_headers_and_logs(response, mock_logger, expected)
