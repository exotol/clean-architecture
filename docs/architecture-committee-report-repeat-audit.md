# Повторный аудит EVA: готовность к production (DAU 5M+)

**Дата:** 2025-03-17  
**Основа:** [Первый отчёт архитектурного комитета](architecture-committee-report.md).  
**Цель:** Проверить текущее состояние по пунктам предыдущего вердикта и обновить оценку.

---

## Сводка изменений с момента первого аудита

| Критерий из первого отчёта | Статус | Что сделано / что осталось |
|---------------------------|--------|----------------------------|
| Rate limiting | ✅ Реализовано | Конфиг `RATE_LIMIT.*`, `RateLimitMiddleware`, `RateLimitStore`, подключение в `app_factory` при `enabled=true`. По умолчанию выключено. |
| Разделение liveness / readiness | ✅ Реализовано | Эндпоинты `/common/live` и `/common/ready`, интерфейс `IReadinessChecker`, `DefaultReadinessChecker` (пока всегда `True`). |
| Конфиг кэша и circuit breaker | ✅ Добавлено | Секции `CACHE.*` и `CIRCUIT_BREAKER.*` в settings, DI-провайдеры `cache_backend`, `circuit_breaker`. Реализации есть (InMemoryCacheBackend, CircuitBreaker). |
| Интеграция кэша/circuit breaker в поиск | ❌ Не сделано | SearchService и SearchRepository не используют кэш и circuit breaker. |
| Утечка в 500: `detail=str(exc)` | ❌ Не исправлено | В `global_exception_handler` по-прежнему `detail=str(exc)` (строка 179). |
| `exc_info=True` в обработчиках ошибок | ❌ Не исправлено | В `infra_error_handler` и `global_exception_handler` вызовы `logger.error(...)` без `exc_info=True`. |
| SearchRepository — реальный бэкенд | ❌ Без изменений | Реализация по-прежнему mock (возврат заглушки). |
| Контракт ответа `{"hello": response}` | ❌ Без изменений | Эндпоинт `/v1/answer/generate` по-прежнему возвращает `{"hello": response}`. |
| CORS / TrustedHost `*` в production | ❌ Без изменений | В `configs/settings.toml` по умолчанию `SECURITY.CORS.ORIGINS = ["*"]`, `SECURITY.TRUSTED.HOSTS = ["*"]`. |
| Readiness проверяет зависимости | ⚠️ Частично | Инфраструктура готова (`/ready`, `IReadinessChecker`), но `DefaultReadinessChecker` не проверяет OpenSearch/БД. |

---

## 1. Оценка по параметрам (обновлённая)

| № | Критерий | Было | Стало | Комментарий |
|---|----------|------|--------|-------------|
| 1 | Архитектурные паттерны | 8 | 8 | Без изменений. Добавлены интерфейсы readiness, cache, circuit_breaker. |
| 2 | Архитектурные антипаттерны | 6 | 6 | Контракт `{"hello": response}` и mock-репозиторий по-прежнему. |
| 3 | Паттерны проектирования | 8 | 8 | Strategy, Factory, Repository, DTO; добавлены middleware и resilience-компоненты. |
| 4 | Антипаттерны проектирования | 5 | 5 | `detail=str(exc)` в 500 и lazy resolution стратегий в monitor не исправлены. |
| 5 | Качество кода | 8 | 8 | Уровень сохранён; новые модули (rate_limit, probes, cache, circuit_breaker) в духе проекта. |
| 6 | Декомпозиция | 8 | 9 | Добавлены слой health (readiness), middleware, resilience, cache без размывания границ. |
| 7 | Общие антипаттерны | 5 | 6 | Rate limit и разделение live/ready устранены. Кэш и circuit breaker в коде есть, но не задействованы в поиске; CORS/TrustedHost и mock-репозиторий остаются. |
| 8 | Соответствие enterprise-стандартам | 6 | 7 | Readiness/liveness, конфигурируемый rate limit, задел под кэш и circuit breaker. Нет проверки зависимостей в readiness и реальной интеграции с OpenSearch. |
| 9 | Удобство разработки | 9 | 9 | Добавлены тесты для rate limit и probes. |
| 10 | Расширяемость | 7 | 8 | Новый use case можно дополнить readiness-проверкой, кэшем и circuit breaker через существующие интерфейсы. |
| 11 | Логирование, мониторинг, трассировка | 7 | 7 | Без изменений: по-прежнему нет `exc_info=True` в HTTP exception handlers. |
| 12 | Продуманность сервиса | 6 | 7 | Учтены рекомендации по защите (rate limit) и пробам; до полного сценария 5M DAU не хватает реального поиска и включения кэша/cb в поток поиска. |

**Сводная оценка готовности к production при DAU 5M+:** **6.5 → 7.0 / 10**. Прогресс есть за счёт rate limit, разделения проб и задела по кэшу/circuit breaker; критичные пункты (утечка в 500, exc_info, реальный репозиторий, контракт API, безопасность дефолтного конфига) по-прежнему не закрыты.

---

## 2. Что улучшилось

- **Rate limiting:** реализован in-memory sliding window, конфиг (окно, лимит, опциональный ключ по заголовку), middleware подключён при `RATE_LIMIT.ENABLED=true`. Готов к включению в production после настройки лимитов.
- **Liveness и readiness:** явное разделение: `/common/live` (процесс жив), `/common/ready` (готовность принимать трафик). Возможность позже подставить checker с проверкой OpenSearch/БД без смены контракта.
- **Конфигурация устойчивости:** секции CACHE и CIRCUIT_BREAKER, провайдеры в DI; реализации InMemoryCacheBackend и CircuitBreaker присутствуют. Остаётся встроить их в поиск (и при необходимости в другие use case).
- **Тесты:** добавлены unit-тесты для rate limit middleware и для probes (liveness/readiness).
- **Структура:** появление `domain/interfaces/readiness.py`, `domain/interfaces/cache.py`, `domain/interfaces/circuit_breaker.py` сохраняет направление зависимостей и упрощает замену реализаций.

---

## 3. Что осталось критичным (блокеры для DAU 5M+)

1. **Утечка внутренней информации в 500:** в `global_exception_handler` в теле ответа клиенту передаётся `detail=str(exc)`. Нужно: в ответ отдавать только общее сообщение (например, `Reasons.internal_server_error.message`) и `trace_id`; полный текст/стек — только в логах.
2. **Нет полного stack trace в логах при 503/500:** в `infra_error_handler` и `global_exception_handler` вызовы `logger.error(...)` без `exc_info=True`. Нужно добавить `exc_info=True`, чтобы в логах был полный traceback.
3. **SearchRepository — mock:** для 5M DAU необходима реальная интеграция с OpenSearch (из docker-compose): таймауты, лимиты размера ответа, при необходимости пулы и retry. Сейчас репозиторий возвращает заглушку.
4. **Контракт ответа поиска:** ответ `{"hello": response}` неочевиден для API. Либо заменить на явный ключ (например `data`), либо отдавать `SearchResponse` в корне и зафиксировать в OpenAPI.
5. **Безопасность дефолтного конфига:** CORS и TrustedHost со значением `*` недопустимы для production. Нужны отдельные конфиги/окружения (например `[production]`) с явными списками origins и hosts.

---

## 4. Что желательно закрыть до высокой нагрузки

- **Readiness с проверкой зависимостей:** реализовать вариант `IReadinessChecker`, который пингует OpenSearch (и при появлении БД — её) и возвращает `False` при недоступности, чтобы оркестратор не слал трафик на неготовый инстанс.
- **Использование кэша и circuit breaker в поиске:** опционально по конфигу подставлять кэш (по ключу запроса) и оборачивать вызов репозитория в circuit breaker, чтобы при 5M DAU снижать нагрузку на поиск и изолировать сбои бэкенда.
- **Документация SLO и алертов:** целевые значения latency/error rate и примеры правил Prometheus/Alertmanager для готовности к эксплуатации.

---

## 5. Вердикт повторного аудита

**Статус:** **условное принятие** (без изменений по сравнению с первым отчётом).

**Итог:** По сравнению с первым аудитом сервис продвинулся: появились rate limiting, разделение liveness/readiness и задел по кэшу и circuit breaker. Оценка слегка выросла (6.5 → 7.0), но **для выхода в production с DAU 5M+ по-прежнему обязательны**:

- исправление утечки в 500 (`detail` не должен содержать `str(exc)`);
- добавление `exc_info=True` в обработчики 503/500;
- реализация реального SearchRepository с OpenSearch;
- приведение контракта ответа поиска к явному виду;
- ужесточение CORS и TrustedHost в production-конфиге.

После выполнения этих пунктов и при необходимости — включения rate limit, readiness с проверкой зависимостей и интеграции кэша/circuit breaker в поиск — рекомендуется повторная проверка и нагрузочное тестирование на целевом масштабе.
