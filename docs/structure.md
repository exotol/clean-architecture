# Структура проекта

## Общий обзор

```
eva/
├── configs/               # Конфигурационные файлы
├── docker/                # Docker-related файлы
├── docs/                  # Документация (вы здесь)
├── profiles/              # Профили производительности (gitignored)
├── scripts/               # Утилитные скрипты
├── src/                   # Исходный код приложения
│   └── app/
├── tests/                 # Тесты
├── Makefile               # Команды автоматизации
├── pyproject.toml         # Зависимости и настройки проекта
└── README.md              # Главный README
```

## Исходный код (`src/app/`)

### Domain (`src/app/domain/`)

Ядро бизнес-логики. **Не имеет внешних зависимостей**.

```
domain/
├── entities/              # Бизнес-сущности
│   └── document.py        # Пример: Document dataclass
└── interfaces/            # Интерфейсы (Protocol/ABC)
    ├── observability.py   # ILoggingStrategy, ITracingStrategy, IMetricsStrategy
    └── search_repository.py # ISearchRepository
```

**Что класть сюда:**
- Dataclasses/Pydantic models, представляющие бизнес-объекты
- Протоколы (interfaces) для репозиториев и сервисов
- Value Objects
- Domain Events
- Domain Services (если содержат чистую бизнес-логику без зависимостей)

### Application (`src/app/application/`)

Сценарии использования (Use Cases).

```
application/
└── services/
    └── search_service.py  # SearchService — оркестрирует бизнес-логику
```

**Что класть сюда:**
- Application Services (Use Cases)
- Application-level DTOs
- Orchestration логику
- Валидацию бизнес-правил

### Infrastructure (`src/app/infrastructure/`)

Реализации интерфейсов и работа с внешним миром.

```
infrastructure/
├── observability/         # Observability stack
│   ├── logging.py         # Настройка loguru
│   ├── metrics.py         # Настройка Prometheus/OpenTelemetry
│   ├── profiling.py       # cProfile middleware
│   └── strategies/
│       ├── logging.py     # StandardLoggingStrategy
│       ├── tracing.py     # OpentelemetryTracingStrategy
│       └── metrics.py     # OpentelemetryMetricsStrategy
├── persistence/           # Работа с данными
│   └── repositories/
│       └── search_repository.py  # SearchRepository implementation
└── services/              # Внешние сервисы
    └── (external API clients)
```

**Что класть сюда:**
- Реализации репозиториев (PostgreSQL, OpenSearch, Redis)
- ORM модели (SQLAlchemy, Tortoise)
- Клиенты внешних API
- Адаптеры для внешних сервисов
- Observability implementations

### Presentation (`src/app/presentation/`)

HTTP API и точки входа.

```
presentation/
└── api/
    ├── v1/                # Версия API
    │   ├── api.py         # Роутер для v1
    │   └── endpoints/
    │       └── search.py  # POST /api/v1/search
    ├── common/            # Общие endpoints (не версионированы)
    │   └── endpoints/
    │       ├── healthcheck.py  # GET /healthcheck
    │       ├── metrics.py      # GET /metrics
    │       └── root.py         # GET /
    ├── schemas/           # Pydantic DTOs
    │   ├── response.py    # Общие response schemas
    │   └── search.py      # SearchRequest, SearchResponse
    ├── application_api.py # Главный роутер
    └── exception_handlers.py # Обработчики исключений
```

**Что класть сюда:**
- FastAPI route handlers
- Pydantic schemas для request/response
- Middleware (CORS, Auth)
- Exception handlers
- API versioning logic

### Core (`src/app/core/`)

Общие компоненты, используемые всеми слоями.

```
core/
├── app_factory.py    # Фабрика FastAPI приложения
├── containers.py     # DI контейнеры
├── constants.py      # Глобальные константы
├── events.py         # Определения событий (Events enum)
└── exceptions.py     # Кастомные исключения
```

**Что класть сюда:**
- DI контейнеры и провайдеры
- Кастомные исключения (BusinessError, InfrastructureError)
- Глобальные константы
- Event definitions

### Utils (`src/app/utils/`)

Утилиты без бизнес-логики.

```
utils/
├── configs.py      # Pydantic config models, load_settings()
├── serializer.py   # ItemSerializer, ORJSONResponse
└── monitor.py      # @monitor декоратор
```

**Что класть сюда:**
- Загрузка конфигурации
- Сериализация/десериализация
- Декораторы общего назначения
- Вспомогательные функции

## Конфигурация (`configs/`)

```
configs/
└── settings.toml   # Основной файл настроек
```

## Скрипты (`scripts/`)

```
scripts/
└── prof_to_speedscope.py  # Конвертер cProfile -> speedscope format
```

## Docker (`docker/`)

```
docker/
├── docker-compose.yml   # Docker Compose для инфраструктуры
└── Dockerfile           # (опционально) Dockerfile приложения
```

## Правила именования

| Тип файла | Конвенция | Пример |
|-----------|-----------|--------|
| Модули | snake_case | `search_service.py` |
| Классы | PascalCase | `SearchService` |
| Интерфейсы | I + PascalCase | `ISearchRepository` |
| Тесты | test_ + имя модуля | `test_search_service.py` |
| Schemas | Model + Request/Response | `SearchRequest`, `SearchResponse` |
| Endpoints | Имя ресурса | `search.py`, `healthcheck.py` |

## Следующие шаги

- [Тестирование](testing.md) — структура тестов
- [Профилирование](profiling.md) — анализ производительности
