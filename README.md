# EVA — Clean Architecture Python Template

Шаблон Python-приложения, построенный на принципах **Clean Architecture**. Демонстрирует лучшие практики организации кода для production-ready сервисов.

## Ключевые особенности

- 🏗️ **Clean Architecture** — четкое разделение слоёв
- 🔌 **Dependency Injection** — dependency-injector
- 📊 **Observability** — логирование (Loguru), трейсинг (OpenTelemetry), метрики (Prometheus)
- ⚡ **High Performance** — Granian ASGI server, orjson serialization
- 🧪 **Data-Driven Testing** — pytest + Pydantic schemas
- 📈 **Profiling** — cProfile middleware, snakeviz, speedscope

## Быстрый старт

```bash
# Установка зависимостей
uv sync

# Запуск приложения
python src/app/main.py

# Запуск тестов
make run.pytest
```

## 📚 Документация

Полная документация находится в директории [`docs/`](docs/README.md):

| Документ | Описание |
|----------|----------|
| [Концепция](docs/concept.md) | Философия проекта и принципы Clean Architecture |
| [Архитектура](docs/architecture.md) | Детальное описание слоёв и зависимостей |
| [Структура проекта](docs/structure.md) | Организация директорий и файлов |
| [Тестирование](docs/testing.md) | Подход к тестированию и запуск тестов |
| [Профилирование](docs/profiling.md) | Инструменты анализа производительности |
| [Makefile команды](docs/makefile.md) | Справочник всех команд автоматизации |
| [Конфигурация](docs/configuration.md) | Описание всех настроек в settings.toml |

## Структура проекта

```
src/app/
├── domain/                # Бизнес-логика (Entities, Interfaces)
├── application/           # Use Cases (Services)
├── infrastructure/        # Реализация (Repositories, Observability)
├── presentation/          # API (FastAPI endpoints, Schemas)
├── core/                  # DI, Exceptions, Constants
└── utils/                 # Utilities
```

## Основные команды

```bash
# Разработка
make ruff.check        # Проверка кода
make ruff.format       # Форматирование
make mypy.check        # Проверка типов

# Инфраструктура
make start.infra       # Запуск Docker-инфраструктуры

# Тестирование
make run.pytest        # Unit/Integration/E2E тесты
make run.load          # Нагрузочное тестирование (Locust)

# Профилирование
make profile.view      # Просмотр профилей в snakeviz
make profile.clean     # Очистка профилей
```

## Конфигурация

Настройки в `configs/settings.toml`. Основные секции:

- `GRANIAN.SERVER` — веб-сервер
- `LOGGING` — логирование
- `METRICS` — Prometheus метрики
- `SECURITY` — CORS, trusted hosts
- `TRACING.OTLP` — OpenTelemetry tracing
- `SERIALIZATION` — настройки сериализации
- `PROFILING` — cProfile middleware

Подробнее: [docs/configuration.md](docs/configuration.md)

## uv + pyenv

```bash
# Чтобы uv использовал окружение pyenv
alias uv='UV_PROJECT_ENVIRONMENT=$VIRTUAL_ENV uv'
```

## License

See [LICENSE](LICENSE) for details.