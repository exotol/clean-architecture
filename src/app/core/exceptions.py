from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import DEFAULT_PROBLEM_DETAIL_TYPE, NO_PARAMS
from app.core.types import Reasons


class ProblemDetail(BaseModel):
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
        ..., description="Короткий программный код ошибки"
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
        ..., description="В каком логе искать детали? (контекст операции)"
    )
    invalid_params: list[dict[str, str]] | None = Field(
        default=NO_PARAMS,
        description="Список полей формы, не прошедших валидацию.",
    )


class AppException(Exception):
    """Базовый класс для всех ошибок приложения."""


class BusinessException(AppException):
    """Бизнес-ошибки (клиент виноват / нарушены правила)."""

    urn_type_error: str | None = Field(
        Reasons.business_rule_violation.urn_type_error
    )
    code: str | None = Field(
        Reasons.business_rule_violation.code,
    )
    title: str | None = Field(
        Reasons.business_rule_violation.title,
    )
    detail: str | None = Field(
        Reasons.business_rule_violation.message,
    )


# --- Инфраструктурные ошибки (система виновата) ---
class InfrastructureException(AppException):
    """
    Инфраструктурные ошибки.

    Cистема виновата: БД упала, S3 не отвечает.

    """
