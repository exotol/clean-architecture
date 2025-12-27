# Концепция проекта

## Что такое EVA?

EVA — это **шаблон Python-приложения**, построенный на принципах **Clean Architecture** (Чистая Архитектура). Проект демонстрирует лучшие практики организации кода для production-ready сервисов.

## Ключевые принципы

### 1. Независимость от фреймворков

Бизнес-логика не зависит от FastAPI, SQLAlchemy или любого другого фреймворка. Фреймворки — это инструменты, которые можно заменить без переписывания core-логики.

### 2. Тестируемость

Каждый слой тестируется изолированно:
- **Unit-тесты** проверяют бизнес-логику без внешних зависимостей
- **Integration-тесты** проверяют взаимодействие с инфраструктурой
- **E2E-тесты** проверяют API endpoints

### 3. Независимость от UI

Проект не привязан к конкретному способу взаимодействия. REST API можно заменить на gRPC, GraphQL или CLI без изменения бизнес-логики.

### 4. Независимость от базы данных

Репозитории абстрагируют доступ к данным. Можно переключиться с OpenSearch на PostgreSQL, изменив только реализацию репозитория.

### 5. Независимость от внешних сервисов

Все внешние зависимости скрыты за интерфейсами. Это позволяет легко мокировать их в тестах и заменять реализации.

## Clean Architecture: The Dependency Rule

```
┌─────────────────────────────────────────────────────────────┐
│                     Presentation Layer                       │
│                   (Controllers, API, CLI)                    │
├─────────────────────────────────────────────────────────────┤
│                     Application Layer                        │
│                   (Use Cases, Services)                      │
├─────────────────────────────────────────────────────────────┤
│                       Domain Layer                           │
│              (Entities, Interfaces, Business Rules)          │
├─────────────────────────────────────────────────────────────┤
│                   Infrastructure Layer                       │
│            (DB, External APIs, Frameworks, I/O)              │
└─────────────────────────────────────────────────────────────┘

           ↑ Dependencies point INWARD ↑
```

**Правило зависимостей**: Зависимости направлены только внутрь. Внутренний слой ничего не знает о внешних слоях.

## Dependency Injection

Проект использует **dependency-injector** для управления зависимостями:

```python
# Определение контейнера
class InfrastructureContainer(containers.DeclarativeContainer):
    search_repository = providers.Singleton(SearchRepository)
    search_service = providers.Singleton(
        SearchService,
        repository=search_repository,
    )
```

Это обеспечивает:
- **Инверсию зависимостей** — модули зависят от абстракций
- **Легкое тестирование** — зависимости можно подменять
- **Прозрачную конфигурацию** — все зависимости видны в одном месте

## Observability: Трейсинг, Логирование, Метрики

Проект реализует **Three Pillars of Observability**:

| Pillar | Implementation |
|--------|----------------|
| **Logging** | Loguru + structured logging |
| **Tracing** | OpenTelemetry |
| **Metrics** | Prometheus via OpenTelemetry |

Все три аспекта объединены через декоратор `@monitor`:

```python
@monitor(
    event_name=Events.SEARCH_SERVICE,
    use_log_args=True,
    use_log_result=True,
)
async def search(self, query: str) -> list[Document]:
    return await self._repository.search(query=query)
```

## Следующие шаги

- [Архитектура](architecture.md) — детальное описание слоёв
- [Структура проекта](structure.md) — организация файлов
- [Тестирование](testing.md) — как писать и запускать тесты
