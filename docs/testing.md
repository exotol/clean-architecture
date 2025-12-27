# Тестирование

## Обзор

Проект использует **pytest** с **data-driven** подходом и строгой типизацией тестовых данных.

## Структура тестов

```
tests/
├── conftest.py            # Глобальные fixtures
├── schemas/               # Тестовые данные (Pydantic models)
│   ├── e2e/               # Данные для E2E тестов
│   ├── integration/       # Данные для интеграционных тестов
│   └── unit/              # Данные для unit тестов
├── e2e/                   # End-to-End тесты (API)
│   └── api/
├── integration/           # Интеграционные тесты
│   └── infrastructure/
├── unit/                  # Unit тесты
│   ├── application/
│   ├── infrastructure/
│   └── utils/
└── performance/           # Нагрузочные тесты (Locust)
    ├── locustfile.py
    ├── users.py
    └── config.py
```

## Типы тестов

### 1. Unit Tests (`tests/unit/`)

Тестируют изолированные модули без внешних зависимостей.

**Что тестируют:**
- Application Services
- Domain logic
- Utilities

**Пример:**
```python
# tests/unit/application/test_search_service.py
@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            SearchServiceEntity(query="test", mock_return=[Document(text="res1")]),
            SearchServiceExpected(count=1, results=[Document(text="res1")]),
            id="success_single_result",
        ),
    ],
)
async def test_search_success(
    search_service: SearchService,
    mock_repository: AsyncMock,
    entity: SearchServiceEntity,
    expected: SearchServiceExpected,
) -> None:
    mock_repository.search.return_value = entity.mock_return
    
    actual_results = await search_service.search(query=entity.query)
    
    assert len(actual_results) == expected.count
```

### 2. Integration Tests (`tests/integration/`)

Тестируют взаимодействие с внешними системами (БД, API).

**Что тестируют:**
- Репозитории с реальной БД
- Внешние API клиенты

**Пример:**
```python
# tests/integration/infrastructure/test_search_repository.py
@pytest.mark.integration
async def test_search_repository_returns_documents():
    repo = SearchRepository()
    results = await repo.search(query="test")
    assert isinstance(results, list)
```

### 3. E2E Tests (`tests/e2e/`)

Тестируют полный flow через HTTP API.

**Что тестируют:**
- API endpoints
- Request/Response schemas
- HTTP status codes

**Пример:**
```python
# tests/e2e/api/test_search_endpoint.py
@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(
            SearchEndpointEntity(query="test"),
            SearchEndpointExpected(status_code=200, has_results=True),
            id="success_with_results",
        ),
    ],
)
async def test_search_endpoint(
    client: AsyncClient,
    entity: SearchEndpointEntity,
    expected: SearchEndpointExpected,
) -> None:
    response = await client.post("/api/v1/search", json={"query": entity.query})
    
    assert response.status_code == expected.status_code
```

### 4. Performance Tests (`tests/performance/`)

Нагрузочные тесты с использованием Locust.

**Файлы:**
- `locustfile.py` — определение тестов
- `users.py` — типы пользователей (load, stress)
- `config.py` — конфигурация

## Data-Driven Testing

### Тестовые схемы

Все тестовые данные описываются через Pydantic models:

```python
# tests/schemas/unit/application/search_service.py
from pydantic import BaseModel

class SearchServiceEntity(BaseModel):
    """Input data for test."""
    query: str
    mock_return: list[Document]

class SearchServiceExpected(BaseModel):
    """Expected results."""
    count: int
    results: list[Document]
```

### Преимущества

1. **Типизация** — IDE подсказывает поля, ошибки видны до запуска
2. **Валидация** — Pydantic проверяет типы данных
3. **Читаемость** — структура данных очевидна
4. **Переиспользование** — схемы можно использовать в разных тестах

## Fixtures

### Глобальные (`tests/conftest.py`)

```python
@pytest.fixture(scope="session")
def app() -> FastAPI:
    """Create FastAPI application."""
    return create_app()

@pytest.fixture(scope="session")
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """HTTP client for E2E tests."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
```

### Unit-тесты (`tests/unit/conftest.py`)

```python
@pytest.fixture(scope="session", autouse=True)
def setup_di_container() -> None:
    """Initialize DI container for unit tests."""
    container = AppContainer()
    container.infra_container().config.from_dict(load_settings().as_dict())
    container.wire(packages=["app"])
```

## Запуск тестов

### Все тесты

```bash
make run.pytest
# или
pytest tests
```

### Конкретный тип

```bash
pytest tests/unit           # Unit tests
pytest tests/integration    # Integration tests
pytest tests/e2e            # E2E tests
```

### С покрытием

```bash
pytest tests --cov=src/app --cov-report=html
```

### Конкретный тест

```bash
pytest tests/unit/application/test_search_service.py::test_search_success -v
```

### Параллельный запуск

```bash
pytest tests -n auto  # требует pytest-xdist
```

## Markers

```python
@pytest.mark.anyio()     # Async test
@pytest.mark.parametrize # Data-driven test
@pytest.mark.integration # Integration test (может быть пропущен)
```

## Best Practices

1. **Один тест — один сценарий**
2. **Используйте `id` в parametrize** для читаемых отчётов
3. **Мокайте внешние зависимости** в unit-тестах
4. **Используйте fixtures** для повторяющейся setup-логики
5. **Описывайте expected** результаты явно

## Следующие шаги

- [Профилирование](profiling.md) — анализ производительности
- [Makefile Commands](makefile.md) — команды запуска
