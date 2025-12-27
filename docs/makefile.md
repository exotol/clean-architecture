# Makefile Commands

Полный справочник команд автоматизации.

## Окружение и установка

### Python и pyenv

| Команда | Описание |
|---------|----------|
| `make install.dep.python` | Установить системные зависимости для сборки Python |
| `make install.pyenv` | Установить pyenv |
| `make install.python` | Установить Python через pyenv |
| `make create.venv` | Создать виртуальное окружение |
| `make remove.venv` | Удалить виртуальное окружение |

**Пример: полная установка окружения**
```bash
make install.dep.python
make install.pyenv
source ~/.bashrc
make install.python
make create.venv
```

### uv (package manager)

| Команда | Описание |
|---------|----------|
| `make install.uv` | Установить uv |
| `make init.uv` | Инициализировать проект с uv |

## Линтеры и форматтеры

| Команда | Описание |
|---------|----------|
| `make ruff.check` | Проверка кода Ruff + автофикс |
| `make ruff.format` | Форматирование кода |
| `make mypy.check` | Проверка типов MyPy |
| `make wemake.run` | Проверка wemake-python-styleguide |

**Пример:**
```bash
# Полная проверка перед коммитом
make ruff.check
make ruff.format
make mypy.check
```

### Pre-commit

| Команда | Описание |
|---------|----------|
| `make install.pre-commit` | Установить pre-commit hooks |
| `make remove.pre-commit` | Удалить pre-commit hooks |

## Инфраструктура

| Команда | Описание |
|---------|----------|
| `make start.infra` | Запустить Docker инфраструктуру |
| `make check.opensearch` | Проверить доступность OpenSearch |
| `make block.off.index` | Снять блокировку индекса на запись |

**Пример:**
```bash
# Запуск инфраструктуры для разработки
make start.infra

# В другом терминале - проверка
make check.opensearch
```

## Тестирование

| Команда | Описание |
|---------|----------|
| `make run.pytest` | Запустить все pytest тесты |

**Пример:**
```bash
make run.pytest
```

## Нагрузочное тестирование

| Команда | Описание |
|---------|----------|
| `make run.load` | Запустить Locust (Web UI) |
| `make run.load ARGS="..."` | Запустить с параметрами |

**Примеры:**
```bash
# Web UI на http://localhost:8089
make run.load

# Headless: 10 users, 2 rps spawn, 30 секунд
make run.load ARGS="--headless -u 10 -r 2 -t 30s"

# Stress test (без пауз)
make run.load ARGS="EvaStressUser --headless -u 50 -r 10 -t 60s"
```

### Параметры Locust

| Параметр | Описание |
|----------|----------|
| `--headless` | Без Web UI |
| `-u N` | Количество пользователей |
| `-r N` | Spawn rate (users/sec) |
| `-t TIME` | Длительность (30s, 5m, 1h) |
| `-H URL` | Хост (default: http://localhost:8000) |

## Профилирование

| Команда | Описание |
|---------|----------|
| `make profile.view` | Открыть последний профиль в snakeviz |
| `make profile.speedscope.view` | Конвертировать профиль для speedscope |
| `make profile.clean` | Удалить все профили |

**Пример:**
```bash
# 1. Включить профилирование в settings.toml
# PROFILING.ENABLED = true

# 2. Запустить приложение и сделать запросы

# 3. Просмотреть профиль
make profile.view

# Или для speedscope
make profile.speedscope.view
# Загрузить .speedscope.json на https://www.speedscope.app/

# 4. Очистка
make profile.clean
```

## Переменные

| Переменная | Default | Описание |
|------------|---------|----------|
| `PYTHON_VERSION` | 3.12 | Версия Python |
| `PYTHON_VENV` | eva | Имя виртуального окружения |
| `ARGS` | (empty) | Аргументы для команд |

## uv + pyenv интеграция

Чтобы uv использовал окружение pyenv:

```bash
# Добавить в .bashrc
alias uv='UV_PROJECT_ENVIRONMENT=$VIRTUAL_ENV uv'
```

## Docker

| Команда | Описание |
|---------|----------|
| `make docker.build` | Сборка Docker образа |
| `make docker.build.no-cache` | Сборка без кеша |
| `make docker.run` | Запуск контейнера |
| `make docker.run.detached` | Запуск в фоновом режиме |
| `make docker.stop` | Остановка контейнера |
| `make docker.logs` | Просмотр логов |
| `make docker.shell` | Shell в контейнере |
| `make docker.size` | Размер образа |
| `make docker.clean` | Удаление образа |

**Переменные:**
- `DOCKER_IMAGE` — имя образа (default: `eva`)
- `DOCKER_TAG` — тег (default: `latest`)

**Примеры:**
```bash
# Сборка с тегом версии
make docker.build DOCKER_TAG=v1.0.0

# Запуск в фоне
make docker.run.detached

# Проверка размера
make docker.size
```

Подробнее: [docs/docker.md](docker.md)

## Следующие шаги

- [Docker](docker.md) — подробности о Docker
- [Configuration](configuration.md) — настройки приложения
