"""Unit tests for application exceptions hierarchy and models."""

from __future__ import annotations

from pydantic import ValidationError
import pytest

from app.core import exceptions
from app.core.exceptions import AppError
from app.core.exceptions import ProblemDetail
from app.core.exceptions import Reasons
from tests.schemas.unit.core.exceptions import AppErrorEntity
from tests.schemas.unit.core.exceptions import AppErrorExpected


@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            AppErrorEntity(
                error_class_name="BusinessError",
                detail=None,
            ),
            AppErrorExpected(
                status_code=400,
                code=Reasons.business_rule_violation.code,
                title=Reasons.business_rule_violation.title,
                detail=Reasons.business_rule_violation.message,
                urn_type_error=Reasons.business_rule_violation.urn_type_error,
                invalid_params=None,
            ),
            id="business_error_default",
        ),
        pytest.param(
            AppErrorEntity(
                error_class_name="BusinessError",
                detail="Invalid quantity",
                kwargs={
                    "invalid_params": [
                        {"name": "quantity", "reason": "negative"},
                    ],
                },
            ),
            AppErrorExpected(
                status_code=400,
                code=Reasons.business_rule_violation.code,
                title=Reasons.business_rule_violation.title,
                detail="Invalid quantity",
                urn_type_error=Reasons.business_rule_violation.urn_type_error,
                invalid_params=[
                    {"name": "quantity", "reason": "negative"},
                ],
            ),
            id="business_error_custom",
        ),
        pytest.param(
            AppErrorEntity(
                error_class_name="InfrastructureError",
                detail=None,
            ),
            AppErrorExpected(
                status_code=503,
                code=Reasons.service_unavailable.code,
                title=Reasons.service_unavailable.title,
                detail=Reasons.service_unavailable.message,
                urn_type_error=Reasons.service_unavailable.urn_type_error,
                invalid_params=None,
            ),
            id="infrastructure_error_default",
        ),
        pytest.param(
            AppErrorEntity(
                error_class_name="InfrastructureError",
                detail="Postgres unreachable",
                kwargs={"service_name": "postgres"},
            ),
            AppErrorExpected(
                status_code=503,
                code=Reasons.service_unavailable.code,
                title=Reasons.service_unavailable.title,
                detail="Postgres unreachable",
                urn_type_error=Reasons.service_unavailable.urn_type_error,
                invalid_params=None,
            ),
            id="infrastructure_error_custom",
        ),
        pytest.param(
            AppErrorEntity(
                error_class_name="RateLimitExceededError",
                detail=None,
            ),
            AppErrorExpected(
                status_code=429,
                code=Reasons.rate_limit_exceeded.code,
                title=Reasons.rate_limit_exceeded.title,
                detail=Reasons.rate_limit_exceeded.message,
                urn_type_error=Reasons.rate_limit_exceeded.urn_type_error,
                invalid_params=None,
            ),
            id="rate_limit_error_default",
        ),
        pytest.param(
            AppErrorEntity(
                error_class_name="RateLimitExceededError",
                detail="Too many calls",
                kwargs={"retry_after": 120.0},
            ),
            AppErrorExpected(
                status_code=429,
                code=Reasons.rate_limit_exceeded.code,
                title=Reasons.rate_limit_exceeded.title,
                detail="Too many calls",
                urn_type_error=Reasons.rate_limit_exceeded.urn_type_error,
                invalid_params=None,
            ),
            id="rate_limit_error_custom",
        ),
        pytest.param(
            AppErrorEntity(
                error_class_name="InnerTechError",
                detail=None,
            ),
            AppErrorExpected(
                status_code=500,
                code=Reasons.internal_server_error.code,
                title=Reasons.internal_server_error.title,
                detail=Reasons.internal_server_error.message,
                urn_type_error=Reasons.internal_server_error.urn_type_error,
                invalid_params=None,
            ),
            id="inner_tech_error_default",
        ),
        pytest.param(
            AppErrorEntity(
                error_class_name="AppError",
                detail="Custom app failure",
                kwargs={
                    "reason": Reasons.validation_error,
                    "status_code": 422,
                },
            ),
            AppErrorExpected(
                status_code=422,
                code=Reasons.validation_error.code,
                title=Reasons.validation_error.title,
                detail="Custom app failure",
                urn_type_error=Reasons.validation_error.urn_type_error,
                invalid_params=None,
            ),
            id="app_error_direct",
        ),
    ],
)
def test_app_error_hierarchy(
    entity: AppErrorEntity,
    expected: AppErrorExpected,
) -> None:
    # Arrange
    error_cls = getattr(exceptions, entity.error_class_name)

    # Act
    kwargs = dict(entity.kwargs)
    if entity.detail is not None:
        if entity.error_class_name == "AppError":
            kwargs["detail"] = entity.detail
            error_instance = error_cls(**kwargs)
        else:
            error_instance = error_cls(entity.detail, **kwargs)
    else:
        error_instance = error_cls(**kwargs)

    # Assert
    assert isinstance(error_instance, AppError), (
        f"Expected {error_instance} to be an instance of AppError"
    )
    assert error_instance.status_code == expected.status_code, (
        f"Expected status_code {expected.status_code}, "
        f"got {error_instance.status_code}"
    )
    assert error_instance.code == expected.code, (
        f"Expected code {expected.code}, got {error_instance.code}"
    )
    assert error_instance.title == expected.title, (
        f"Expected title {expected.title}, got {error_instance.title}"
    )
    assert error_instance.detail == expected.detail, (
        f"Expected detail {expected.detail}, got {error_instance.detail}"
    )
    assert error_instance.urn_type_error == expected.urn_type_error, (
        f"Expected urn_type_error {expected.urn_type_error}, "
        f"got {error_instance.urn_type_error}"
    )
    assert error_instance.invalid_params == expected.invalid_params, (
        f"Expected invalid_params {expected.invalid_params}, "
        f"got {error_instance.invalid_params}"
    )


def test_reasons_registry_is_immutable() -> None:
    # Arrange
    original = Reasons.internal_server_error

    # Act
    with pytest.raises(TypeError, match="Cannot modify immutable reason"):
        Reasons.internal_server_error = original

    # Assert
    assert Reasons.internal_server_error == original, (
        "Reasons registry should not allow attribute reassignment"
    )


def test_reason_instance_is_immutable() -> None:
    # Arrange
    reason = Reasons.internal_server_error

    # Act
    with pytest.raises(ValidationError):
        reason.code = "MUTATED"

    # Assert
    assert reason.code == "INTERNAL_SERVER_ERROR", (
        "Reason model instances must be frozen"
    )


def test_problem_detail_model_dump_alias() -> None:
    # Arrange
    problem = ProblemDetail(
        urn_type_error="urn:problem:test",
        title="Test Error",
        status=400,
        reason="TEST_CODE",
        detail="Test message",
        instance="/api/test",
        trace_id="test-trace",
    )

    # Act
    dumped = problem.model_dump(by_alias=True, exclude_none=True)

    # Assert
    assert dumped["type"] == "urn:problem:test", (
        f"Expected alias 'type' to be 'urn:problem:test', "
        f"got {dumped.get('type')}"
    )
    assert dumped["title"] == "Test Error", (
        f"Expected title 'Test Error', got {dumped.get('title')}"
    )
    assert dumped["status"] == 400, (
        f"Expected status 400, got {dumped.get('status')}"
    )
