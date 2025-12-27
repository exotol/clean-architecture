An implementation of Clean Architecture principles. Feel free to use it!



Настройка для Ruff (Format + Fix Imports):

    Name: Ruff Fix

    File type: Python

    Scope: Project Files

    Program: ruff (или полный путь к ruff в venv, например $PyInterpreterDirectory$/ruff)

    Arguments: check --fix --select I $FilePath$ (Для исправления импортов) или check --fix $FilePath$ (Для всего).

    Output paths to refresh: $FilePath$

    Working directory:ы $ProjectFileDir$

    Advanced Options:

        Снимите галочку "Auto-save edited files to trigger the watcher" (чтобы не запускалось при каждом нажатии клавиши).

        Оставьте "Trigger the watcher on explicit save" (при Ctrl+S).


⚠️ Критически важно: Отключить встроенные "улучшайзеры" PyCharm

Чтобы PyCharm не воевал с Ruff/Isort, нужно отключить его встроенную сортировку импортов, иначе они будут бесконечно менять файл туда-сюда.

    Отключите сортировку импортов:

        Settings -> Editor -> General -> Auto Import.

        Убедитесь, что Optimize imports on the fly отключено (для Python).

    Настройте Docstrings (чтобы не было конфликтов с кавычками):

        Settings -> Editor -> Code Style -> Python -> Docstrings.

        Если Ruff настроен на двойные кавычки, убедитесь, что PyCharm не форсирует одинарные.

    Отключите назойливые инспекции PyCharm (которые дублируют Ruff):

        Если Ruff уже проверяет PEP8, можно выключить PEP8 проверки в PyCharm:

        Settings -> Editor -> Inspections -> Python -> PEP 8 coding style violation (снять галочку).



* Мониторинг 
  * Обработка разных видов исключений
* Отладка проброса исключений
* 3 либы для логирования
  * standard logger
  * logure
  * structure logger
* линтеры
* Обновить документацию


## Архитектура проекта

Проект построен на принципах **Clean Architecture** (Чистая Архитектура), что обеспечивает разделение ответственности, тестируемость и независимость от фреймворков.

### Слои (Layers)

#### 1. Domain (`src/app/domain`)
Ядро бизнес-логики. Не зависит ни от каких внешних библиотек или фреймворков.
*   **entities/**: Бизнес-сущности (чистые классы или dataclasses).
*   **interfaces/**: Интерфейсы (протоколы/ABC) для репозиториев и внешних сервисов.

#### 2. Application (`src/app/application`)
Слой сценариев использования (Use Cases). Оркестрирует бизнес-логику.
*   **services/**: Сервисы приложения, реализующие конкретные бизнес-сценарии.
*   *Зависит только от Domain.*

#### 3. Infrastructure (`src/app/infrastructure`)
Реализация интерфейсов и работа с внешним миром.
*   **persistence/**: Работа с БД (репозитории, ORM модели).
*   **observability/**: Логирование, мониторинг, трейсинг (Events, Monitor).
*   **services/**: Инфраструктурные сервисы (метрики, клиенты API).
*   *Зависит от Domain и Application.*

#### 4. Presentation (`src/app/presentation`)
Точка входа в приложение (API).
*   **api/v1/endpoints/**: Обработчики HTTP-запросов (FastAPI).
*   **api/schemas/**: Pydantic-схемы для валидации запросов и ответов.
*   *Зависит от Application.*

#### 5. Core & Utils (`src/app/core`, `src/app/utils`)
Общие компоненты.
*   **core/**: DI-контейнеры, исключения, константы, декораторы.
*   **utils/**: Загрузка конфигурации.

### Структура проекта

```text
src/app/
├── domain/                    # Business Core (No Deps)
│   ├── entities/              # Business Objects
│   └── interfaces/            # Interfaces (Ports)
│
├── application/               # Use Cases
│   └── services/              # Application Services
│
├── infrastructure/            # Implementation Details
│   ├── persistence/           # Database & Repositories
│   ├── observability/         # Logging, Tracing, Events
│   └── services/              # Infrastructure Services
│
├── presentation/              # API & Entry Points
│   └── api/
│       ├── v1/endpoints/      # Route Handlers
│       └── schemas/           # Pydantic Models (DTOs)
│
├── core/                      # Shared Kernel
│   ├── containers.py          # Dependency Injection
│   ├── exceptions.py          # Custom Exceptions
│   └── constants.py           # Global Constants
│
└── utils/                     # Utilities
    └── configs.py             # Configuration Management
```

## Тестирование (Testing)

Тесты используют **Data-Driven** подход и строгую типизацию.

### Подход
*   **Data-Driven Tests**: Все тесты используют `pytest.mark.parametrize` с явными `id` для каждого кейса.
*   **Pydantic Models**: Вместо `dataclasses` используются Pydantic-модели для описания входных данных (`Entity`) и ожидаемых результатов (`Expected`).
*   **Reusability**: Схемы приложения (`app.presentation.api.schemas`) переиспользуются в E2E тестах.
*   **Separation of Concerns**: Тестовые сущности вынесены в отдельную директорию `tests/schemas`.

### Структура тестов

```text
tests/
├── schemas/                   # Test Data Definitions (Pydantic)
│   ├── e2e/                   # Schemas for E2E tests
│   ├── integration/           # Schemas for Integration tests
│   └── unit/                  # Schemas for Unit tests
│
├── e2e/                       # End-to-End Tests (API)
│   └── api/
│       ├── test_search_endpoint.py
│       ├── test_healthcheck_endpoint.py
│       └── test_root_endpoint.py
│
├── integration/               # Integration Tests (DB, Infra)
│   └── infrastructure/
│       └── test_search_repository.py
│
├── unit/                      # Unit Tests (Business Logic)
│   └── application/
│       └── test_search_service.py
│
└── conftest.py                # Global Fixtures (App, Client, Async)
```

### Запуск тестов

Запуск всех тестов:
```bash
pytest tests
```

Запуск линтеров и форматтеров (Pre-commit):
```bash
pre-commit run --all-files
```

## Performance Testing

We use [Locust](https://locust.io/) for load testing.

### Running Tests
To start the Locust Web UI:
```bash
make run.load
```
Then open http://localhost:8089 in your browser.

### Headless Mode (CI/CD)
To run tests without UI (e.g., for 30 seconds with 10 users):
```bash
make run.load ARGS="--headless -u 10 -r 2 -t 30s"
```

### Stress Testing (Max RPS)
To run a stress test with no wait time between requests:
```bash
make run.load ARGS="EvaStressUser --headless -u 10 -r 2 -t 30s"
```

# Как заставить UV использовать указанное ей окружение (другие способы не заработали)
# Вставляет текущий $VIRTUAL_ENV в переменную конфигурации UV перед запуском
```
alias uv='UV_PROJECT_ENVIRONMENT=$VIRTUAL_ENV uv'
```

1.