import uuid

from fastapi import Request
from fastapi import status as http_status
from fastapi.responses import JSONResponse
from loguru import logger

from app.core.constants import NO_PARAMS
from app.core.constants import TRACE_ID
from app.core.constants import USER_ID
from app.core.exceptions import ProblemDetail
from app.core.exceptions import Reasons


def business_error_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    Обработчик нарушений бизнес-правил.

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
        f"Business rule violation: {code} - {detail_msg}",
        exc_info=True,
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
    """
    Обработчик ошибок инфраструктуры.

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
    # exc_info=True запишет полный стек-трейс в логи
    logger.error(
        f"Infrastructure error: {exc!s}",
        exc_info=True,
        extra={"trace_id": trace_id},
    )

    problem = ProblemDetail(
        # Используем алиас 'type' для удобства (если в ConfigDict разрешили)
        urn_type_error=Reasons.service_unavailable.urn_type_error,
        title=Reasons.service_unavailable.title,
        status=http_status.HTTP_503_SERVICE_UNAVAILABLE,
        # Код для фронтенда, чтобы показать экран "Технические работы"
        reason=Reasons.service_unavailable.code,
        # ВАЖНО: не пишите str(exc) ("Connection refused 127.0.0.1:5432")
        detail=Reasons.service_unavailable.message,
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


def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Глобальный обработчик.

    Eсли что-то просочилось через декоратор

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
    # exc_info=True запишет полный стек-трейс в логи
    logger.error(
        "Unhandled exception (0)".format(),
        exc_info=True,
        extra={"trace_id": trace_id, "exc_extra_info": str(exc)},
    )

    # 3. Собираем модель ответа (ДЛЯ КЛИЕНТА)
    problem = ProblemDetail(
        # Используем имя поля класса, Pydantic сам
        # переименует его в 'type' благодаря alias
        urn_type_error=Reasons.internal_server_error.urn_type_error,
        title=Reasons.internal_server_error.title,
        status=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        reason=Reasons.internal_server_error.code,
        # ВАЖНО: Не показываем str(exc) пользователю в 500 ошибке!
        detail=str(exc),  # Reasons.internal_server_error.message,
        instance=request.url.path,  # URI, где упало
        trace_id=trace_id,
        invalid_params=NO_PARAMS,  # Для 500 ошибки это поле не актуально
    )

    # Тут можно отправить алерт в Sentry
    return JSONResponse(
        status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
        # model_dump(by_alias=True) нужен, чтобы
        # urn_type_error превратился в type
        # exclude_none=True уберет пустые поля (invalid_params)
        content=problem.model_dump(by_alias=True, exclude_none=True),
    )


def request_validation_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    Обработчик ошибок валидации Pydantic/FastAPI.
    """
    trace_id = (
        getattr(request.state, TRACE_ID, None)
        or request.headers.get(TRACE_ID, None)
        or str(uuid.uuid4())
    )

    # Логируем как warning
    logger.warning(
        "Validation error: {errors}",
        errors=exc.errors(),
        extra={"trace_id": trace_id},
    )

    # Преобразуем ошибки Pydantic в наш формат
    invalid_params = []
    for error in exc.errors():
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
