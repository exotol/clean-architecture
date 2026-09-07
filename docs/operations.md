# Эксплуатация сервиса

## Служебные endpoints

Все общие endpoints доступны с префиксом `/common`:

| Endpoint | Назначение | Успешный ответ |
|----------|------------|----------------|
| `GET /common/healthcheck` | Проверка доступности HTTP-приложения | `200` |
| `GET /common/live` | Liveness: процесс работает | `200`, `{"status":"ok"}` |
| `GET /common/ready` | Readiness: сервис готов принимать трафик | `200`, `{"status":"ok"}` |
| `GET /common/metrics` | Prometheus-метрики | `200`, text/plain |

`/common/live` не проверяет внешние зависимости. Текущая реализация `/common/ready` использует `DefaultReadinessChecker`, который всегда возвращает готовность; при подключении базы данных или поискового backend’а его следует заменить через DI.

Для Kubernetes обычно используют `/common/live` для `livenessProbe`, а `/common/ready` — для `readinessProbe`.

## Защита от перегрузки

При `RATE_LIMIT.ENABLED = true` middleware применяет скользящее окно. Клиент идентифицируется заголовком `RATE_LIMIT.KEY_HEADER` или IP-адресом. При превышении лимита возвращаются `429`, RFC 7807 body и `Retry-After`.

Rate limit store, cache и circuit breaker — in-memory и привязаны к экземпляру процесса. При нескольких воркерах или репликах состояние не синхронизируется.

## Cache и circuit breaker

`InMemoryCacheBackend` предоставляет операции `get`, `set` и `delete`, TTL по умолчанию задаётся через `CACHE.TTL_SECONDS`, а переполнение ограничивается `CACHE.MAX_SIZE` с LRU-вытеснением.

`CircuitBreaker` оборачивает async-функции и имеет состояния `closed`, `open` и `half-open`. После `CIRCUIT_BREAKER.FAILURE_THRESHOLD` ошибок цепь открывается, а после `CIRCUIT_BREAKER.RECOVERY_TIMEOUT_SECONDS` допускается пробный вызов.

Подробные параметры находятся в [configuration.md](configuration.md).
