# Профилирование и производительность

## Обзор

Проект предоставляет инструменты для анализа производительности на разных уровнях:

| Инструмент | Тип | Когда использовать |
|------------|-----|-------------------|
| **cProfile** | Deterministic | Точный анализ каждого вызова |
| **Locust** | Load testing | Нагрузочное тестирование API |
| **snakeviz** | Visualization | Визуализация профилей |
| **speedscope** | Visualization | Flame charts в браузере |

## cProfile Middleware

### Включение

Профилирование включается через `settings.toml`:

```toml
PROFILING.ENABLED = true
PROFILING.OUTPUT_DIR = "profiles"
PROFILING.SORT_BY = "cumulative"
PROFILING.TOP_N = 50
```

### Как работает

1. При `PROFILING.ENABLED = true` middleware профилирует каждый HTTP-запрос
2. Профиль сохраняется в `profiles/` с именем: `{timestamp}_{method}_{path}.prof`
3. В логи выводятся топ-N функций по времени

### Параметры

| Параметр | Описание | Default |
|----------|----------|---------|
| `ENABLED` | Включить/выключить профилирование | `false` |
| `OUTPUT_DIR` | Директория для профилей | `profiles` |
| `SORT_BY` | Сортировка: `cumulative`, `time`, `calls` | `cumulative` |
| `TOP_N` | Количество функций в логах | `50` |

> **⚠️ Важно:** Не включайте профилирование в production — это добавляет overhead.

## Просмотр профилей

### snakeviz (интерактивный)

```bash
# Установка
pip install snakeviz

# Просмотр последнего профиля
make profile.view
```

Откроется браузер с интерактивной визуализацией:

```
┌─────────────────────────────────────────────────────────────┐
│                     main (100% - 1.234s)                     │
├─────────────────────────────────────────────────────────────┤
│  search_service.search (45%)  │  serialize (30%)  │ other  │
├───────────────────────────────┼───────────────────┼────────┤
│       repository.search       │     orjson.dumps  │        │
└───────────────────────────────┴───────────────────┴────────┘
```

### speedscope (flame charts)

```bash
# Конвертация профиля в speedscope формат
make profile.speedscope.view

# Откройте созданный .speedscope.json на https://www.speedscope.app/
```

### Очистка профилей

```bash
make profile.clean
```

## Нагрузочное тестирование (Locust)

### Запуск

```bash
# Web UI (http://localhost:8089)
make run.load

# Headless режим (для CI/CD)
make run.load ARGS="--headless -u 10 -r 2 -t 30s"
```

### Параметры

| Параметр | Описание |
|----------|----------|
| `-u 10` | 10 пользователей |
| `-r 2` | 2 пользователя в секунду (spawn rate) |
| `-t 30s` | Длительность теста |
| `--headless` | Без UI |

### Типы пользователей

```python
# tests/performance/users.py

class EvaUser(HttpUser):
    """Standard load testing user with wait time."""
    wait_time = between(0.5, 2)

class EvaStressUser(HttpUser):
    """Stress testing user - no wait time, max RPS."""
    wait_time = constant(0)
```

### Stress Test

```bash
# Максимальная нагрузка (без пауз между запросами)
make run.load ARGS="EvaStressUser --headless -u 50 -r 10 -t 60s"
```

## Интерпретация результатов

### cProfile output

```
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
      100    0.050    0.001    1.234    0.012 search_service.py:16(search)
      100    0.800    0.008    0.800    0.008 repository.py:25(query_db)
      300    0.100    0.000    0.300    0.001 serializer.py:42(serialize)
```

| Колонка | Описание |
|---------|----------|
| `ncalls` | Количество вызовов |
| `tottime` | Время в функции (без вложенных) |
| `percall` | tottime / ncalls |
| `cumtime` | Время с вложенными вызовами |

### На что смотреть

1. **Высокий tottime** — функция делает много работы
2. **Высокий cumtime при низком tottime** — проблема во вложенных вызовах
3. **Много ncalls** — возможно, лишние вызовы (N+1 problem)

## Best Practices

### 1. Профилируйте реалистичные сценарии

```bash
# Запустите приложение
python src/app/main.py &

# Включите профилирование в settings.toml

# Отправьте реальную нагрузку
make run.load ARGS="--headless -u 5 -r 1 -t 30s"

# Анализируйте профили
make profile.view
```

### 2. Сравнивайте до и после

```bash
# Before optimization
cp profiles/latest.prof profiles/before.prof

# After optimization
cp profiles/latest.prof profiles/after.prof

# Compare
python3 -c "
import pstats
before = pstats.Stats('profiles/before.prof')
after = pstats.Stats('profiles/after.prof')
print('BEFORE:'); before.sort_stats('cumulative').print_stats(10)
print('AFTER:'); after.sort_stats('cumulative').print_stats(10)
"
```

### 3. Изолируйте bottleneck

Если функция занимает много времени:
1. Проверьте вложенные вызовы (cumtime vs tottime)
2. Проверьте количество вызовов (ncalls)
3. Добавьте более детальное профилирование для конкретного участка

## Следующие шаги

- [Makefile Commands](makefile.md) — все команды автоматизации
- [Configuration](configuration.md) — настройки приложения
