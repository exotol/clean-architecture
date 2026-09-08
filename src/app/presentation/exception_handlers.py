from __future__ import annotations

import logging
import uuid

from fastapi import Request
from fastapi import status as http_status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.constants import NO_PARAMS
from app.core.constants import TRACE_ID
from app.core.constants import USER_ID
from app.core.exceptions import ProblemDetail
from app.core.exceptions import Reasons


logger = logging.getLogger(__name__)


def business_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Обработчик нарушений бизнес-правил.

    Ожидает, что exc может иметь атрибуты: status_code, code, detail.

    Args:
        request: Объект входящего запроса.
        exc: Перехваченное исключение (бизнес-логики).

    Returns:
        JSONResponse с сформированной структурой ошибки (ProblemDetail).
    """
    # Сначала ищем в state (если middleware положил),
    # потом в хедерах, иначе генерируем новый
    trace_id = (
        getattr(request.state, TRACE_ID, None)
        or request.headers.get(TRACE_ID, None)
        or str(uuid.uuid4())
    )

    # 2. Извлекаем данные из исключения
    # Пытаемся взять статус из ошибки (если это кастомный класс), иначе 400
    status_code = getattr(exc, "status_code", http_status.HTTP_400_BAD_REQUEST)

    # Пытаемся взять внутренний код (например, 'USER_BLOCKED'), иначе дефолт
    code = getattr(exc, "code", Reasons.business_rule_violation.code)

    # Сообщение для юзера. В бизнес-ошибках безопасно делать str(exc)
    detail_msg = getattr(exc, "detail", str(exc))

    # 3. Логируем как WARNING (не ERROR!)
    # не нужен стек-трейс для бизнес-логики, достаточно факта ошибки
    # но для детального разбора лучше давать и stack trace
    logger.warning(
        "Business rule violation: %s - %s",
        code,
        detail_msg,
        extra={
            "trace_id": trace_id,
            "user_id": request.headers.get(USER_ID),
        },
    )

    # 4. Формируем ответ
    problem = ProblemDetail(
        # Генерируем URN динамически на основе кода ошибки
        urn_type_error=getattr(
            exc,
            "urn_type_error",
            Reasons.business_rule_violation.urn_type_error,
        ),
        title=getattr(exc, "title", Reasons.business_rule_violation.title),
        status=status_code,
        reason=code,
        # ВАЖНО: Здесь мы ПОКАЗЫВАЕМ текст ошибки пользователю
        detail=detail_msg,
        instance=request.url.path,
        trace_id=trace_id,
        # Если в ошибке есть список некорректных параметров (опционально)
        invalid_params=getattr(exc, "invalid_params", NO_PARAMS),
    )

    return JSONResponse(
        status_code=status_code,
        content=problem.model_dump(by_alias=True, exclude_none=True),
    )


def infra_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Обработчик ошибок инфраструктуры.

    БД, Redis, Celery, внешние API.

    Args:
        request: Объект входящего запроса.
        exc: Перехваченное исключение (бизнес-логики).

    Returns:
        JSONResponse с сформированной структурой ошибки (ProblemDetail).
    """
    # Сначала ищем в state (если middleware положил),
    # потом в хедерах, иначе генерируем новый
    trace_id = (
        getattr(request.state, TRACE_ID, None)
        or request.headers.get(TRACE_ID, None)
        or str(uuid.uuid4())
    )

    # 2. Логируем реальную ошибку (ДЛЯ РАЗРАБОТЧИКА)
    logger.error(
        "Infrastructure error: %s",
        exc,
        extra={"trace_id": trace_id},
    )

    problem = ProblemDetail(
        # Используем алиас 'type' для удобства (если в ConfigDict разрешили)
        urn_type_error=getattr(
            exc,
            "urn_type_error",
            Reasons.service_unavailable.urn_type_error,
        ),
        title=getattr(exc, "title", Reasons.service_unavailable.title),
        status=getattr(
            exc,
            "status_code",
            http_status.HTTP_503_SERVICE_UNAVAILABLE,
        ),
        # Код для фронтенда, чтобы показать экран "Технические работы"
        reason=getattr(exc, "code", Reasons.service_unavailable.code),
        # ВАЖНО: не пишите str(exc) ("Connection refused 127.0.0.1:5432")
        detail=getattr(exc, "detail", Reasons.service_unavailable.message),
        instance=request.url.path,
        trace_id=trace_id,
        # invalid_params здесь не нужны
        invalid_params=NO_PARAMS,
    )

    return JSONResponse(
        status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
        # by_alias=True превратит urn_type_error -> type
        content=problem.model_dump(by_alias=True, exclude_none=True),
        # Хорошим тоном для 503 ошибки является заголовок Retry-After
        headers={"Retry-After": "30"},
    )


def rate_limit_error_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Обработчик превышения лимита запросов.

    Args:
        request: Объект входящего запроса.
        exc: Перехваченное исключение (RateLimitExceededError).

    Returns:
        JSONResponse с ProblemDetail и заголовком Retry-After.
    """
    trace_id = (
        getattr(request.state, TRACE_ID, None)
        or request.headers.get(TRACE_ID, None)
        or str(uuid.uuid4())
    )
    retry_after_int = max(1, int(getattr(exc, "retry_after", 60.0)))
    status_code = getattr(
        exc,
        "status_code",
        http_status.HTTP_429_TOO_MANY_REQUESTS,
    )
    detail_msg = getattr(exc, "detail", Reasons.rate_limit_exceeded.message)
    code = getattr(exc, "code", Reasons.rate_limit_exceeded.code)

    logger.warning(
        "Rate limit exceeded: %s - %s",
        code,
        detail_msg,
        extra={"trace_id": trace_id},
    )

    problem = ProblemDetail(
        urn_type_error=getattr(
            exc,
            "urn_type_error",
            Reasons.rate_limit_exceeded.urn_type_error,
        ),
        title=getattr(exc, "title", Reasons.rate_limit_exceeded.title),
        status=status_code,
        reason=code,
        detail=detail_msg,
        instance=request.url.path,
        trace_id=trace_id,
        invalid_params=NO_PARAMS,
    )
    return JSONResponse(
        status_code=status_code,
        content=problem.model_dump(by_alias=True, exclude_none=True),
        headers={"Retry-After": str(retry_after_int)},
    )


def global_exception_handler(
    request: Request,
    exc: Exception,
    *,
    use_exposed_details: bool = False,
) -> JSONResponse:
    """Глобальный обработчик для необработанных исключений.

    Args:
        request: Объект входящего запроса.
        exc: Перехваченное исключение.
        use_exposed_details: Флаг для локального дебага (утечка str(exc)).

    Returns:
        JSONResponse с сформированной структурой ошибки (ProblemDetail).
    """
    trace_id = (
        getattr(request.state, TRACE_ID, None)
        or request.headers.get(TRACE_ID, None)
        or str(uuid.uuid4())
    )

    # 2. Логируем реальную ошибку со стек-трейсом (ДЛЯ РАЗРАБОТЧИКА)
    logger.error(
        "Unhandled exception (0)",
        extra={"trace_id": trace_id, "exc_extra_info": str(exc)},
    )

    app_state = getattr(getattr(request, "app", None), "state", None)
    is_exposed = use_exposed_details or bool(
        getattr(app_state, "use_exposed_details", False),
    )
    detail_msg = (
        str(exc) if is_exposed else Reasons.internal_server_error.message
    )

    # 3. Собираем модель ответа (ДЛЯ КЛИЕНТА)
    problem = ProblemDetail(
        urn_type_error=Reasons.internal_server_error.urn_type_error,
        title=Reasons.internal_server_error.title,
        status=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        reason=Reasons.internal_server_error.code,
        detail=detail_msg,
        instance=request.url.path,
        trace_id=trace_id,
        invalid_params=NO_PARAMS,
    )

    return JSONResponse(
        status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=problem.model_dump(by_alias=True, exclude_none=True),
    )


def request_validation_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Обработчик ошибок валидации Pydantic/FastAPI."""
    trace_id = (
        getattr(request.state, TRACE_ID, None)
        or request.headers.get(TRACE_ID, None)
        or str(uuid.uuid4())
    )

    # Логируем как warning
    validation_exc = exc if isinstance(exc, RequestValidationError) else None
    errors = validation_exc.errors() if validation_exc is not None else []
    logger.warning(
        "Validation error: %s",
        errors,
        extra={"trace_id": trace_id},
    )

    # Преобразуем ошибки Pydantic в наш формат
    invalid_params = []
    for error in errors:
        loc = ".".join(str(x) for x in error.get("loc", []))
        msg = error.get("msg", "Unknown error")
        invalid_params.append({loc: msg})

    problem = ProblemDetail(
        urn_type_error=Reasons.validation_error.urn_type_error,
        title=Reasons.validation_error.title,
        status=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
        reason=Reasons.validation_error.code,
        detail=Reasons.validation_error.message,
        instance=request.url.path,
        trace_id=trace_id,
        invalid_params=invalid_params,
    )

    return JSONResponse(
        status_code=http_status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=problem.model_dump(by_alias=True, exclude_none=True),
    )
