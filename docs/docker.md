# Docker

## Обзор

Проект использует **multi-stage Docker build** для создания оптимизированного production-ready образа.

## Структура

```
docker/
├── Dockerfile           # Production Dockerfile
└── docker-compose.yml   # Инфраструктура (OpenSearch, etc.)
```

## Dockerfile: Оптимизации

| Оптимизация | Описание | Эффект |
|-------------|----------|--------|
| **Multi-stage build** | Сборка и runtime в разных стейджах | Размер ~100MB vs ~1GB |
| **python:3.12-slim** | Минимальный базовый образ | ~50MB base |
| **uv для зависимостей** | Быстрый package manager | Сборка в 10x быстрее pip |
| **BuildKit cache mount** | Кеширование между сборками | Инкрементальные сборки |
| **Layer ordering** | Зависимости до кода | Лучшее кеширование |
| **Non-root user** | Запуск от `appuser:appgroup` | Безопасность |
| **PYTHONOPTIMIZE=2** | Удаление docstrings, assert | Меньше памяти, быстрее |
| **PYTHONDONTWRITEBYTECODE** | Без .pyc файлов | Чище образ |
| **Healthcheck** | Встроенная проверка | Kubernetes readiness |

## Стейджи сборки

```
┌─────────────────────────────────────────────────────────────┐
│  Stage 1: Builder                                            │
│  - Установка uv                                              │
│  - Копирование pyproject.toml, uv.lock                      │
│  - Установка зависимостей (с кешированием)                  │
│  - Копирование исходного кода                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  Stage 2: Runtime                                            │
│  - Только python:3.12-slim                                   │
│  - Копирование .venv из builder                             │
│  - Копирование src/ и configs/                               │
│  - Non-root user                                             │
│  - Healthcheck                                               │
└─────────────────────────────────────────────────────────────┘
```

## Makefile команды

| Команда | Описание |
|---------|----------|
| `make docker.build` | Сборка образа |
| `make docker.build.no-cache` | Сборка без кеша |
| `make docker.run` | Запуск контейнера |
| `make docker.run.detached` | Запуск в фоне |
| `make docker.stop` | Остановка контейнера |
| `make docker.logs` | Просмотр логов |
| `make docker.shell` | Shell в контейнере |
| `make docker.size` | Размер образа |
| `make docker.clean` | Удаление образа |

### Переменные

| Переменная | Default | Описание |
|------------|---------|----------|
| `DOCKER_IMAGE` | eva | Имя образа |
| `DOCKER_TAG` | latest | Тег образа |

### Примеры

```bash
# Сборка с кастомным тегом
make docker.build DOCKER_TAG=v1.0.0

# Запуск в фоне
make docker.run.detached

# Проверка логов
make docker.logs

# Проверка размера
make docker.size
# eva:latest - 120MB

# Остановка
make docker.stop
```

## Запуск вручную

```bash
# Сборка
docker build -f docker/Dockerfile -t eva:latest .

# Запуск
docker run -p 8000:8000 eva:latest

# С переменными окружения
docker run -p 8000:8000 \
  -e LOGGING__LEVEL=DEBUG \
  -e GRANIAN__SERVER__WORKERS=4 \
  eva:latest

# С volume для configs
docker run -p 8000:8000 \
  -v $(pwd)/configs:/app/configs:ro \
  eva:latest
```

## Docker Compose

Для локальной разработки с инфраструктурой:

```bash
make start.infra
# Запускает OpenSearch через docker-compose.yml
```

## Production рекомендации

### 1. Не используйте `latest` тег

```bash
make docker.build DOCKER_TAG=$(git rev-parse --short HEAD)
```

### 2. Сканируйте на уязвимости

```bash
docker scan eva:latest
# или
trivy image eva:latest
```

### 3. Ограничьте ресурсы

```bash
docker run -p 8000:8000 \
  --memory=512m \
  --cpus=1 \
  eva:latest
```

### 4. Используйте read-only filesystem

```bash
docker run -p 8000:8000 \
  --read-only \
  --tmpfs /tmp \
  eva:latest
```

## Kubernetes

Пример Deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: eva
spec:
  replicas: 3
  selector:
    matchLabels:
      app: eva
  template:
    metadata:
      labels:
        app: eva
    spec:
      containers:
      - name: eva
        image: eva:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /healthcheck
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /healthcheck
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

## Следующие шаги

- [Makefile Commands](makefile.md) — все команды
- [Configuration](configuration.md) — настройки через переменные окружения
