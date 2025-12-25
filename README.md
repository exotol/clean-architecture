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
  * простой декоратор
  * типизированный декоратор
  * opentelemetry
    * логирование 
    * логирование + id
    * логирование + metrics
  * Обработка разных видов исключений
* Отладка проброса исключений



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