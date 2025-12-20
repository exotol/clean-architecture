from enum import StrEnum

from pydantic import BaseModel


class Events(StrEnum):
    start = "START"
    stop = "STOP"


class Reason(BaseModel):
    urn_type_error: str
    code: str
    message: str
    title: str


class Reasons:
    internal_server_error = Reason(
        urn_type_error="urn:error:internal-server-error",
        code="INTERNAL_SERVER_ERROR",
        message=(
            "An unexpected error occurred. "
            "Please contact support with trace_id."
        ),
        title="Internal Server Error",
    )
    service_unavailable = Reason(
        urn_type_error="urn:error:service-unavailable",
        code="INFRASTRUCTURE_ERROR",
        message=(
            "The service is temporarily unavailable. "
            "Please contact support with trace_id."
        ),
        title="Service Unavailable",
    )
    business_rule_violation = Reason(
        urn_type_error="urn:problem:business-rule-violation",
        code="BUSINESS_RULE_VIOLATION",
        message="The business rule violation.",
        title="Business Rule Violation",
    )
