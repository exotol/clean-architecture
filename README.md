An implementation of Clean Architecture principles. Feel free to use it!



Настройка для Ruff (Format + Fix Imports):

    Name: Ruff Fix

    File type: Python

    Scope: Project Files

    Program: ruff (или полный путь к ruff в venv, например $PyInterpreterDirectory$/ruff)

    Arguments: check --fix --select I $FilePath$ (Для исправления импортов) или check --fix $FilePath$ (Для всего).

    Output paths to refresh: $FilePath$

    Working directory: $ProjectFileDir$

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



Schema & Entity Separation
src/app/
├── domain/                    # BUSINESS CORE (no framework deps)
│   ├── entities/              # Business objects with behavior
│   │   └── search_result.py   # class SearchResult (business logic)
│   └── interfaces/            # Ports (ABCs for repositories/gateways)
│       └── search_repository.py  # class ISearchRepository(ABC)
│
├── application/               # USE CASES
│   ├── services/              # Application services (orchestration)
│   │   └── search_service.py
│   └── dto/                   # Internal transfer objects
│       └── search_dto.py      # Between layers, not API-specific
│
├── infrastructure/            # EXTERNAL CONCERNS
│   ├── persistence/           # Database
│   │   ├── models/            # ORM models (SQLAlchemy)
│   │   │   └── search_model.py  # class SearchORM(Base)
│   │   └── repositories/      # Concrete repository implementations
│   │       └── search_repository.py
│   ├── gateways/              # External API clients
│   └── services/              # Infrastructure services
│       └── metrics.py         # MetricsService
│
├── presentation/              # ENTRY POINTS
│   └── api/
│       ├── v1/
│       │   └── endpoints/
│       │       └── search.py
│       └── schemas/           # API Request/Response schemas
│           └── search.py      # SearchRequest, SearchResponse (Pydantic)
│
└── core/                      # SHARED UTILITIES
    ├── config.py
    ├── containers.py
    ├── decorators.py
    ├── exceptions.py
    └── protocols.py           # NEW: Protocol definitions for typing

Layer Responsibilities
Layer	                            Contains	        BaseModel Location
presentation/api/schemas/	        API DTOs	        SearchRequest, SearchResponse
application/dto/	                Internal DTOs	    Service-to-service transfer
domain/entities/	                Business entities	Plain classes or dataclasses
infrastructure/persistence/models/	DB models	        SQLAlchemy ORM

Test Reorganization
tests/
├── unit/              # Isolated, fast, mock dependencies
│   ├── domain/
│   └── application/
├── integration/       # Real DB, real dependencies
│   └── infrastructure/
├── e2e/               # Full API tests
│   └── api/
└── conftest.py