import json
from typing import Any
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from fastapi import Request
from fastapi import status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.core.exceptions import BusinessError
from app.core.exceptions import InfrastructureError
from app.core.exceptions import Reasons
from app.presentation.api import exception_handlers
from tests.schemas.unit.presentation.exception_handlers import ExceptionHandlerEntity
from tests.schemas.unit.presentation.exception_handlers import ExceptionHandlerExpected



def create_error(cls: type[Exception], **kwargs: Any) -> Exception:
    e = cls()
    for k, v in kwargs.items():
        setattr(e, k, v)
    return e


@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        # Business Error
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
                log_level="WARNING",
            ),
            id="business_error",
        ),
        # Infrastructure Error
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
                log_level="ERROR",
            ),
            id="infra_error",
        ),
        # Global Exception
        pytest.param(
            ExceptionHandlerEntity(
                handler_name="global_exception_handler",
                exception=ValueError("Unexpected Error"),
            ),
            ExceptionHandlerExpected(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content_type_error=Reasons.internal_server_error.urn_type_error,
                content_title=Reasons.internal_server_error.title,
                content_reason=Reasons.internal_server_error.code,
                log_level="ERROR",
            ),
            id="global_exception",
        ),
        # Request Validation Error
        pytest.param(
            ExceptionHandlerEntity(
                handler_name="request_validation_handler",
                exception=RequestValidationError(
                    [{"loc": ("body", "field"), "msg": "field required", "type": "value_error.missing"}]
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
    mock_request = MagicMock(spec=Request)
    mock_request.url.path = entity.request_url
    
    # Configure state to return a string for trace_id
    # TRACE_ID is "X-Request-ID", so we must use setattr because it has hyphens
    from app.core.constants import TRACE_ID
    mock_request.state = MagicMock()
    setattr(mock_request.state, TRACE_ID, "test-trace-id")
    
    mock_request.headers.get.return_value = None

    handler_func = getattr(exception_handlers, entity.handler_name)

    with patch("app.presentation.api.exception_handlers.logger") as mock_logger:
        # Act
        response = handler_func(mock_request, entity.exception)

        # Assert
        assert response.status_code == expected.status_code
        
        content = json.loads(response.body)
        # Check type (aliased to 'type') or urn_type_error
        type_field = content.get("type", content.get("urn_type_error"))
        assert type_field == expected.content_type_error
        assert content["title"] == expected.content_title
        assert content["reason"] == expected.content_reason
        
        if expected.log_level == "WARNING":
            mock_logger.warning.assert_called_once()
        elif expected.log_level == "ERROR":
            mock_logger.error.assert_called_once()
