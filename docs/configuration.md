# Конфигурация

Все настройки приложения хранятся в `configs/settings.toml` и загружаются через [Dynaconf](https://www.dynaconf.com/).

## Неприкосновенные правила качества (в т.ч. для агентов)

- **Запрещено подавлять проверки в коде**: `# noqa`, `# type: ignore` и аналоги недопустимы.
- **Запрещено самовольно добавлять игноры в `pyproject.toml`** (например `extend-per-file-ignores`, `ignore` и т.п.).
- **Любая проблема должна решаться**, а не скрываться подавлением линтера/типов.

## Структура файла

```toml
[default]  # Настройки по умолчанию

SECTION.KEY = value
```

## Разделы настроек

### GRANIAN.SERVER — Web-сервер

**Потребитель:** `src/app/main.py` → Granian ASGI server

| Ключ | Тип | Default | Описание |
|------|-----|---------|----------|
| `PORT` | int | 8000 | Порт сервера |
| `HOST` | str | "0.0.0.0" | Адрес привязки |
| `WORKERS` | int | 1 | Количество воркеров |
| `RELOAD` | bool | false | Авто-перезагрузка при изменениях |
| `FACTORY` | bool | true | Использовать app factory |
| `TARGET_RUN` | str | "app.core.app_factory:create_app" | Точка входа |
| `LOG_LEVEL` | str | "info" | Уровень логов сервера |
| `LOG_ACCESS` | bool | true | Логировать access запросы |

### LOGGING — Логирование

**Потребитель:** `src/app/infrastructure/observability/logging.py` → structlog + stdlib

| Ключ | Тип | Default | Описание |
|------|-----|---------|----------|
| `LEVEL` | str | "INFO" | Минимальный уровень логов |
| `FORMAT` | str | (см. ниже) | Формат вывода (legacy, для совместимости) |
| `PATH` | str | "@none" | Путь к файлу (`@none` = только stdout) |
| `ROTATION` | str | "10 MB" | Ротация файлов |
| `RETENTION` | str | "10 days" | Хранение архивов |
| `LOGGERS_TO_ROOT` | list | [...] | Логгеры для перенаправления в общий handler |
| `LOG_FORMAT` | "json" \| "text" | "json" | `json` — production/парсеры; `text` — локальная разработка (цветной консольный вывод) |
| `MUTE_LOGGERS` | list[str] | [] | Имена логгеров, которые нужно заглушить (NullHandler), например `["httpx", "httpcore"]` |

**Формат по умолчанию (FORMAT):**
```toml
LOGGING.FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | ..."
```

### METRICS — Prometheus метрики

**Потребитель:** `src/app/infrastructure/observability/metrics.py` → OpenTelemetry

| Ключ | Тип | Default | Описание |
|------|-----|---------|----------|
| `SERVICE_NAME` | str | "eva" | Имя сервиса в метриках |
| `DURATION.BUCKETS` | list[float] | [0.005...10.0] | Бакеты для гистограмм |

**Бакеты:**
```toml
METRICS.DURATION.BUCKETS = [
    0.005, 0.01, 0.025, 0.05, 0.075, 0.1,  # 5-100ms
    0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0  # 250ms-10s
]
```

### SECURITY — Безопасность

**Потребитель:** `src/app/core/app_factory.py` → Middleware

| Ключ | Тип | Default | Описание |
|------|-----|---------|----------|
| `CORS.ORIGINS` | list[str] | ["*"] | Разрешённые origins |
| `CORS.ALLOW.CREDENTIALS` | bool | true | Разрешить credentials |
| `CORS.ALLOW.METHODS` | list[str] | ["*"] | Разрешённые HTTP методы |
| `CORS.ALLOW.HEADERS` | list[str] | ["*"] | Разрешённые заголовки |
| `TRUSTED.HOSTS` | list[str] | ["*"] | Доверенные хосты |

> **⚠️ Production:** Замените `["*"]` на конкретные значения!

### TRACING.OTLP — OpenTelemetry трейсинг

**Потребитель:** `src/app/infrastructure/observability/strategies/tracing.py`

| Ключ | Тип | Default | Описание |
|------|-----|---------|----------|
| `ENABLED` | bool | false | Включить экспорт трейсов |
| `ENDPOINT` | str | "console" | URL OTLP collector или "console" |
| `SERVICE_NAME` | str | "eva" | Имя сервиса в трейсах |
| `INSECURE` | bool | false | Использовать HTTP вместо HTTPS |

**Примеры:**
```toml
# Вывод в консоль (разработка)
TRACING.OTLP.ENDPOINT = "console"

# Jaeger (production)
TRACING.OTLP.ENABLED = true
TRACING.OTLP.ENDPOINT = "http://jaeger:4317"
```

### SERIALIZATION — Сериализация

**Потребитель:** `src/app/utils/serializer.py` → ItemSerializer

| Ключ | Тип | Default | Описание |
|------|-----|---------|----------|
| `MAX_DEPTH` | int | 500 | Максимальная глубина вложенности |
| `WARN_DEPTH` | int | 100 | Глубина для предупреждения |
| `MAX_OBJECTS` | int | 100000 | Лимит объектов |
| `DETECT_CYCLES` | bool | true | Обнаруживать циклические ссылки |
| `FALLBACK_ON_ERROR` | bool | true | Fallback при ошибках |
| `USE_ORJSON` | bool | true | Использовать orjson (быстрый) |

### PROFILING — Профилирование

**Потребитель:** `src/app/infrastructure/observability/profiling.py`

| Ключ | Тип | Default | Описание |
|------|-----|---------|----------|
| `ENABLED` | bool | false | Включить профилирование |
| `OUTPUT_DIR` | str | "profiles" | Директория для .prof файлов |
| `SORT_BY` | str | "cumulative" | Сортировка (cumulative/time/calls) |
| `TOP_N` | int | 50 | Топ функций в логах |

> **⚠️ Production:** `ENABLED = false` — профилирование добавляет overhead!

### RATE_LIMIT — Ограничение частоты запросов

**Потребитель:** `src/app/infrastructure/middleware/rate_limit.py` → `RateLimitMiddleware`

Ограничение работает в памяти каждого процесса по скользящему окну. Ключом служит значение заголовка `KEY_HEADER`, если он задан и присутствует в запросе; иначе используется IP клиента.

| Ключ | Тип | Default | Описание |
|------|-----|---------|----------|
| `ENABLED` | bool | false | Включить middleware |
| `REQUESTS_PER_WINDOW` | int | 100 | Максимум запросов за окно |
| `WINDOW_SECONDS` | float | 60.0 | Размер окна в секундах |
| `KEY_HEADER` | str | "" | Заголовок для группировки клиентов; пустое значение — IP |

При превышении лимита сервис возвращает `429 Too Many Requests`, тело в формате RFC 7807 и заголовок `Retry-After`.

> **Production:** при нескольких воркерах лимит считается отдельно в каждом процессе. Для общего лимита между репликами нужен внешний shared store.

### CACHE — In-memory cache

**Потребитель:** `src/app/infrastructure/cache/memory.py` → `InMemoryCacheBackend`

| Ключ | Тип | Default | Описание |
|------|-----|---------|----------|
| `ENABLED` | bool | false | Флаг включения кэша в интеграциях |
| `TTL_SECONDS` | int | 300 | TTL записи по умолчанию |
| `MAX_SIZE` | int | 10000 | Максимальное число записей |

Кэш хранится в памяти процесса, удаляет просроченные записи при чтении и использует LRU-вытеснение при переполнении. Значение TTL, переданное в `set`, имеет приоритет над настройкой по умолчанию.

> Кэш не является общим между воркерами и не переживает перезапуск процесса.

### CIRCUIT_BREAKER — Защита внешних вызовов

**Потребитель:** `src/app/infrastructure/resilience/circuit_breaker.py` → `CircuitBreaker`

| Ключ | Тип | Default | Описание |
|------|-----|---------|----------|
| `ENABLED` | bool | false | Включить circuit breaker |
| `FAILURE_THRESHOLD` | int | 5 | Число ошибок до открытия цепи |
| `RECOVERY_TIMEOUT_SECONDS` | float | 30.0 | Пауза перед переходом в half-open |

Компонент оборачивает асинхронные вызовы. В состоянии `open` новые вызовы завершаются `RuntimeError`; после timeout выполняется пробный вызов. Успешный вызов в `half-open` возвращает цепь в `closed`. Состояние хранится в экземпляре, который регистрируется через DI.

### HTTP_CLIENT — HTTP-клиенты

**Потребитель:** конфигурация транспорта HTTP-клиентов (`httpx`)

| Ключ | Тип | Default | Описание |
|------|-----|---------|----------|
| `BASE_URL` | str | "http://localhost" | Базовый URL внешнего сервиса |
| `TIMEOUT_SECONDS` | float | 30.0 | Общий таймаут запроса |
| `MAX_CONNECTIONS` | int | 100 | Максимальное число соединений |
| `MAX_KEEPALIVE_CONNECTIONS` | int | 20 | Максимум keep-alive соединений |
| `KEEPALIVE_EXPIRY_SECONDS` | float | 5.0 | Время жизни keep-alive соединения |

## Environments

Dynaconf поддерживает разные окружения. Добавьте секции:

```toml
[default]
LOGGING.LEVEL = "INFO"

[development]
LOGGING.LEVEL = "DEBUG"
GRANIAN.SERVER.RELOAD = true

[production]
LOGGING.LEVEL = "WARNING"
SECURITY.CORS.ORIGINS = ["https://myapp.com"]
```

Переключение через переменную окружения:
```bash
export ENV_FOR_DYNACONF=production
python src/app/main.py
```

## Переменные окружения

Dynaconf автоматически читает переменные окружения:

```bash
# Переопределить настройку
export GRANIAN__SERVER__PORT=9000
export LOGGING__LEVEL=DEBUG
```

Формат: `SECTION__SUBSECTION__KEY` (двойное подчёркивание)

## Загрузка конфигурации

```python
from app.utils.configs import load_settings

settings = load_settings()
print(settings.GRANIAN.SERVER.PORT)  # 8000
```

## Pydantic Config Models

Для type-safe доступа используются Pydantic модели:

```python
# src/app/utils/configs.py

class LoggerConfig(BaseModel):
    level: LogLevel
    format: str
    path: str | None
    rotation: str
    retention: str

class ProfilingConfig(BaseModel):
    enabled: bool = False
    output_dir: str = "profiles"
    sort_by: str = "cumulative"
    top_n: int = 50
```

## Best Practices

1. **Не храните секреты в settings.toml** — используйте `.env` или переменные окружения
2. **Разделяйте окружения** — development, staging, production
3. **Документируйте изменения** — обновляйте эту документацию при добавлении настроек
4. **Валидируйте настройки** — используйте Pydantic модели
