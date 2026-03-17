# Тестирование

## Обзор

Проект использует **pytest** с **data-driven** подходом и строгой типизацией тестовых данных.

## Стандарт написания тестов (обязателен для агентов)

Все тесты (unit, integration, e2e) **должны** соответствовать этому стандарту. Агенты и контрибьюторы не имеют права ослаблять или обходить эти правила.

### 1. Структура AAA (Arrange — Act — Assert)

- В каждом тесте явно помечайте три секции комментариями: `# Arrange`, `# Act`, `# Assert`.
- **Arrange** — подготовка данных, моков, конфигурации.
- **Act** — вызов проверяемого кода (в рамках одного кейса parametrize — один Act).
- **Assert** — проверки результата; каждая проверка — отдельный `assert` с сообщением (см. п. 3).

### 2. Data-driven и parametrize

- Если у тестируемого поведения **два и более однотипных сценария** (разные входы/ожидания при той же логике) — тест **обязательно** оформляется через `@pytest.mark.parametrize`. Целевое количество сценариев в одном тесте — **от 7+** (где применимо).
- Имена параметров: `("entity", "expected")`. Входные данные — в типе `*Entity`, ожидаемый результат — в типе `*Expected`.
- Схемы Entity/Expected хранятся в `tests/schemas/`: в `tests/schemas/unit/`, `tests/schemas/integration/`, `tests/schemas/e2e/` в соответствии с типом теста. Использовать Pydantic `BaseModel` или `dataclass` с явными типами.
- У каждого варианта в parametrize **обязателен** осмысленный `id=...` (латиница, snake_case или короткое описание), чтобы в отчёте pytest было понятно, какой сценарий упал.

Формат:

```python
@pytest.mark.parametrize(
    ("entity", "expected"),
    [
        pytest.param(MyEntity(...), MyExpected(...), id="success_case"),
        pytest.param(MyEntity(...), MyExpected(...), id="error_case"),
    ],
)
def test_something(entity: MyEntity, expected: MyExpected) -> None:
    # Arrange
    ...
    # Act
    result = ...
    # Assert
    assert result == expected.value, (f"Expected {expected.value}, got {result}")
```

- Исключение: один уникальный сценарий без вариаций (например, один хендлер с одной проверкой) может быть без parametrize, но при появлении второго аналогичного сценария тест переводится на parametrize.

### 3. Assert с сообщением

- **Запрещено** использовать «голый» assert: `assert x == y`.
- **Обязательно** для каждого assert указывать сообщение в формате:  
  `assert условие, (f"описание: ожидалось ..., получено ...")`  
  чтобы при падении теста было сразу ясно, что именно не совпало (actual vs expected).
- Проверки вызовов моков (call_count, call_args) тоже оформляются через явный assert с сообщением, а не только через `.assert_called_once()` без пояснения.

### 4. Один тест — много сценариев (от 7+)

- Один тест (одна функция) покрывает **много сценариев** за счёт `@pytest.mark.parametrize`: каждый кейс (entity/expected) — отдельный сценарий. Цель — **от 7+ сценариев** в одном тесте, где это применимо. Не плодить отдельные функции теста для каждого варианта; объединять однотипные сценарии в один тест с parametrize.

### 5. Итоговый чек-лист для каждого теста

- [ ] Есть комментарии `# Arrange`, `# Act`, `# Assert`.
- [ ] Два и более однотипных сценария — использован `@pytest.mark.parametrize(("entity", "expected"), ..., id=...)`; цель — от 7+ кейсов в одном тесте где применимо.
- [ ] Entity/Expected из `tests/schemas/...` (или локальные типы с явной структурой).
- [ ] У каждого assert есть сообщение с фактическим и ожидаемым значением.
- [ ] Покрытие не снижается; новый код покрыт тестами.

---

## Неприкосновенные правила качества (в т.ч. для агентов)

- **Запрещено подавлять проверки в коде**: `# noqa`, `# type: ignore` и аналоги недопустимы.
- **Запрещено самовольно добавлять игноры в `pyproject.toml`** (например `extend-per-file-ignores`, `ignore` и т.п.).
- **Любая проблема должна решаться**, а не скрываться подавлением линтера/типов.

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

**Пример (стандарт: AAA, parametrize, assert с сообщением):**
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
    # Arrange
    mock_repository.search.return_value = entity.mock_return

    # Act
    actual_results = await search_service.search(query=entity.query)

    # Assert
    assert len(actual_results) == expected.count, (
        f"Expected count {expected.count}, got {len(actual_results)}"
    )
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

**Пример (стандарт: AAA, parametrize, assert с сообщением):**
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
    # Act
    response = await client.post("/api/v1/search", json={"query": entity.query})

    # Assert
    assert response.status_code == expected.status_code, (
        f"Expected status {expected.status_code}, got {response.status_code}"
    )
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

1. **Один тест — от 7+ сценариев:** объединять однотипные случаи в один тест с parametrize (entity/expected + id); целевое число кейсов — от 7+ где применимо.
2. **Обязательно `id` в parametrize** — для читаемых отчётов и однозначной идентификации сценария.
3. **Мокайте внешние зависимости** в unit-тестах.
4. **Используйте fixtures** для повторяющейся setup-логики.
5. **Описывайте expected** явно в схемах; каждый assert — с сообщением (actual vs expected).

## Следующие шаги

- [Профилирование](profiling.md) — анализ производительности
- [Makefile Commands](makefile.md) — команды запуска
