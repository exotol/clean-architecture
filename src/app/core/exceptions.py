from __future__ import annotations

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from app.core.constants import DEFAULT_PROBLEM_DETAIL_TYPE
from app.core.constants import NO_PARAMS


class Reason(BaseModel):
    """Reason metadata for Problem Details."""

    model_config = ConfigDict(frozen=True)

    urn_type_error: str = Field(..., description="URN типа ошибки")
    code: str = Field(..., description="Строковый код ошибки")
    message: str = Field(..., description="Человекочитаемое сообщение ошибки")
    title: str = Field(..., description="Краткий заголовок ошибки")


class _ReasonsMeta(type):
    """Metaclass ensuring Reasons cannot be modified at runtime."""

    def __setattr__(cls, name: str, value: object) -> None:
        msg = f"Cannot modify immutable reason '{name}'"
        raise TypeError(msg)


class Reasons(metaclass=_ReasonsMeta):
    """Common error reasons used across the service."""

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
    validation_error = Reason(
        urn_type_error="urn:problem:validation-error",
        code="VALIDATION_ERROR",
        message="Request validation failed",
        title="Validation Error",
    )
    rate_limit_exceeded = Reason(
        urn_type_error="urn:error:rate-limit-exceeded",
        code="RATE_LIMIT_EXCEEDED",
        message="Too many requests. Please retry after the indicated time.",
        title="Rate Limit Exceeded",
    )


class ProblemDetail(BaseModel):
    """RFC 7807-like error response model."""

    # В Pydantic v2 лучше использовать model_config вместо class Config
    model_config = ConfigDict(
        populate_by_name=True,
    )

    urn_type_error: str = Field(
        default=DEFAULT_PROBLEM_DETAIL_TYPE,
        description=(
            "Ссылка на документацию или код ошибки "
            "urn:myapp:error-code, пример "
            "urn:error:insufficient-funds"
        ),
        serialization_alias="type",
    )
    title: str = Field(
        ...,
        description=(
            "Краткая, человекочитаемая суть проблемы. "
            "Она не должна меняться от экземпляра к "
            "экземпляру одной и той же ошибки."
        ),
    )
    status: int = Field(
        ...,
        description=(
            "HTTP статус-код. Дублирует статус "
            "ответа сервера, чтобы его можно было "
            "сохранить в теле JSON (полезно при "
            "проксировании)."
        ),
    )
    reason: str | None = Field(
        ...,
        description="Короткий программный код ошибки",
    )
    detail: str | None = Field(
        ...,
        description=(
            "Подробное описание именно этого случая возникновения ошибки."
        ),
    )
    instance: str | None = Field(
        ...,
        description=(
            "Ссылка на конкретный инстанс ошибки. "
            "Обычно это URI запроса, который вызвал "
            "ошибку, или уникальный ID."
            "Где произошла ошибка (контекст ресурса)"
            "Если ошибка не привязана к конкретному ресурсу "
            "(например, «Глобальная ошибка базы данных» или "
            "«Сервис недоступен»), поле instance часто "
            "не заполняют"
        ),
    )
    trace_id: str | None = Field(
        ...,
        description="В каком логе искать детали? (контекст операции)",
    )
    invalid_params: list[dict[str, str]] | None = Field(
        default=NO_PARAMS,
        description="Список полей формы, не прошедших валидацию.",
    )


class AppError(Exception):
    """Базовый класс для всех ошибок приложения."""

    def __init__(
        self,
        *,
        reason: Reason,
        status_code: int,
        detail: str | None = None,
        invalid_params: list[dict[str, str]] | None = None,
    ) -> None:
        """Инициализация базовой ошибки приложения.

        Args:
            reason: Метаданные причины ошибки (код, заголовок, URN).
            status_code: Рекомендуемый HTTP статус-код.
            detail: Подробное описание ошибки (или дефолт из reason).
            invalid_params: Опциональный список параметров с
                ошибками валидации.
        """
        self.reason = reason
        self.status_code = status_code
        self.detail = detail or reason.message
        self.code = reason.code
        self.title = reason.title
        self.urn_type_error = reason.urn_type_error
        self.invalid_params = invalid_params
        super().__init__(self.detail)


class BusinessError(AppError):
    """Бизнес-ошибки (клиент виноват / нарушены правила)."""

    def __init__(
        self,
        detail: str | None = None,
        *,
        reason: Reason = Reasons.business_rule_violation,
        status_code: int = 400,
        invalid_params: list[dict[str, str]] | None = None,
    ) -> None:
        """Инициализация бизнес-ошибки с дефолтным reason и статусом 400."""
        super().__init__(
            reason=reason,
            status_code=status_code,
            detail=detail,
            invalid_params=invalid_params,
        )


class InfrastructureError(AppError):
    """Инфраструктурные ошибки (система виновата: БД упала, S3 не отвечает)."""

    def __init__(
        self,
        detail: str | None = None,
        *,
        reason: Reason = Reasons.service_unavailable,
        status_code: int = 503,
        service_name: str | None = None,
    ) -> None:
        """Инициализация инфраструктурной ошибки со статусом 503."""
        self.service_name = service_name
        super().__init__(
            reason=reason,
            status_code=status_code,
            detail=detail,
        )


class RateLimitExceededError(AppError):
    """Превышение лимита запросов (429 Too Many Requests)."""

    def __init__(
        self,
        detail: str | None = None,
        *,
        retry_after: float = 60.0,
        reason: Reason = Reasons.rate_limit_exceeded,
        status_code: int = 429,
    ) -> None:
        """Инициализация ошибки превышения лимита запросов."""
        self.retry_after = retry_after
        super().__init__(
            reason=reason,
            status_code=status_code,
            detail=detail,
        )


class InnerTechError(AppError):
    """Raised when serialization or internal technical operation fails."""

    def __init__(
        self,
        detail: str | None = None,
        *,
        reason: Reason = Reasons.internal_server_error,
        status_code: int = 500,
    ) -> None:
        """Инициализация внутренней технической ошибки."""
        super().__init__(
            reason=reason,
            status_code=status_code,
            detail=detail,
        )
