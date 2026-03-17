# Отчёт архитектурного комитета: готовность EVA к production (DAU 5M+)

**Дата:** 2025-03-17  
**Цель:** Глубокий анализ сервиса EVA и оценка готовности к production при DAU ≥ 5M пользователей.  
**Состав комитета:** 9 членов (3 Principal Architect — Oracle; 3 Principal Research Engineer — Anthropic; 3 Principal Architect — NASA).

## Неприкосновенные правила качества (в т.ч. для агентов)

- **Запрещено подавлять проверки в коде**: `# noqa`, `# type: ignore` и аналоги недопустимы.
- **Запрещено самовольно добавлять игноры в `pyproject.toml`** (например `extend-per-file-ignores`, `ignore` и т.п.).
- **Любая проблема должна решаться**, а не скрываться подавлением линтера/типов.

---

## 1. Оценка по параметрам

| № | Критерий | Оценка (1–10) | Комментарий |
|---|----------|----------------|-------------|
| 1 | **Архитектурные паттерны** | 8 | Clean Architecture, чёткие слои (Domain → Application → Infrastructure → Presentation), DI (dependency-injector), Protocol-based interfaces. Нет явного CQRS/Event Sourcing для масштаба. |
| 2 | **Архитектурные антипаттерны** | 6 | Есть: Presentation знает о структуре ответа `{"hello": response}` (странный контракт); Core/containers зависят от Infrastructure (импорт конкретных стратегий); один репозиторий — mock, нет реальной персистенции для 5M DAU. |
| 3 | **Паттерны проектирования** | 8 | Strategy (logging/tracing/metrics), Factory (app_factory), Repository, DTO (Pydantic schemas). Мониторинг через декоратор @monitor — единообразно. |
| 4 | **Антипаттерны проектирования** | 5 | Lazy resolution стратегий в `_MonitoringHandler` через @inject при первом обращении (скрытая зависимость от DI context). Глобальный `detail=str(exc)` в 500 ответе — утечка внутренней информации. |
| 5 | **Качество кода** | 8 | Ruff strict, mypy strict, типизация, docstrings, нет mutable globals. Исключения в serializer/monitor обоснованы. |
| 6 | **Декомпозиция** | 8 | Модули небольшие, один класс/файл по смыслу, разделение domain/application/infrastructure/presentation выдержано. Utils (configs, serializer, monitor) используются по назначению. |
| 7 | **Общие антипаттерны** | 5 | Нет rate limiting, кэширования, circuit breaker, retry policy; FileHandler для логов без rotation в коде (rotation задаётся в config, но handler — FileHandler); SearchRepository — заглушка; CORS `*` в дефолте. |
| 8 | **Соответствие enterprise-стандартам** | 6 | Есть: DI, observability (logs, metrics, tracing), RFC 7807 errors, healthcheck, non-root Docker. Нет: rate limit, caching, circuit breaker, SLA-метрик, readiness/liveness разделения, секреты только в config (но нет Vault/внешнего хранилища). |
| 9 | **Удобство разработки** | 9 | Makefile, pre-commit, data-driven тесты, schemas в tests/schemas, docs/, AGENTS.md. Быстрый цикл: make check → ruff, mypy, unit+cov. |
| 10 | **Расширяемость** | 7 | Добавление нового use case (новый сервис + репозиторий + endpoint) — по шаблону понятно. Нет плагинной модели или явных extension points для сторонних интеграций. |
| 11 | **Логирование, мониторинг, трассировка** | 7 | Loguru-подобный конфиг через stdlib logging + json, OpenTelemetry (tracing, metrics), Prometheus, correlation ID. Нет `exc_info=True` в global/infra handlers — потеря stack trace в логах; метрики по event/status/duration есть, но нет SLO/error budget. |
| 12 | **Продуманность сервиса** | 6 | Хорошая база под рост, но: нет реального поиска (OpenSearch в compose есть, репозиторий — mock), нет сценариев при 5M DAU (масштабирование workers, шардирование, кэш). |

**Сводная оценка готовности к production при DAU 5M+:** **6.5 / 10** — фундамент сильный, но для указанного масштаба недостаточно реализовано по персистенции, защите от перегрузки и полноте observability.

---

## 2. Плюсы (по членам комитета)

**Principal Architect (Oracle) #1**  
- Чёткая слоистая архитектура и Dependency Rule соблюдены; порты в Domain, адаптеры в Infrastructure.  
- DI централизован в контейнерах, подмена в тестах удобна.  
- RFC 7807 и единый формат ошибок — хорошо для фронта и поддержки.

**Principal Architect (Oracle) #2**  
- Конфигурация через Dynaconf и Pydantic, без размазывания `os.getenv`.  
- Docker: multi-stage, non-root, HEALTHCHECK.  
- Строгие линтеры и типы (Ruff, mypy) — предсказуемое качество кода.

**Principal Architect (Oracle) #3**  
- Observability через стратегии (ILoggingStrategy, IMetricsStrategy, ITracingStrategy) — легко подменить реализацию.  
- Декоратор @monitor даёт единую точку логирования/метрик/трейсинга по use case.  
- Data-driven тесты и схемы в tests/schemas повышают поддерживаемость.

**Principal Research Engineer (Anthropic) #1**  
- Минимум зависимостей, понятная структура; нет «магии» кроме DI.  
- Fail-safe сериализатор с лимитами глубины/циклов — разумная защита от переполнения при логировании.  
- Типизация и аннотации последовательны; TYPE_CHECKING для обратных зависимостей используется правильно.

**Principal Research Engineer (Anthropic) #2**  
- Документация (architecture, structure, testing) и AGENTS.md задают контекст для людей и агентов.  
- Профилирование (cProfile, snakeviz, speedscope) и Locust заложены в процесс.  
- Корреляция запросов (CorrelationIdMiddleware) — база для трассировки.

**Principal Research Engineer (Anthropic) #3**  
- Domain без внешних зависимостей — тестируемость и переносимость.  
- Протоколы (ISearchRepository, observability) не привязаны к конкретной реализации.  
- Покрытие 95% и порог в coverage — дисциплина качества.

**Principal Architect (NASA) #1**  
- Безопасность: non-root в контейнере, нет хардкода секретов в коде.  
- Обработка ошибок разделена (business / infra / validation / global), Retry-After для 503.  
- Константы и события вынесены в core; конфиг — в одном месте.

**Principal Architect (NASA) #2**  
- Makefile и `make check` как единая точка входа для качества (ruff, mypy, unit+cov).  
- Pre-commit и правила в .cursor/ и AGENTS.md снижают риск поломки при коммитах.  
- Границы слоёв и импорты (только app.*) соблюдены.

**Principal Architect (NASA) #3**  
- Тесты разделены на unit/integration/e2e/performance; data-driven подход с Pydantic-схемами.  
- Метрики Prometheus и гистограммы длительности с настраиваемыми buckets.  
- Версионирование API (v1) и общие эндпоинты (healthcheck, metrics) вынесены отдельно.

---

## 3. Минусы (по членам комитета)

**Principal Architect (Oracle) #1**  
- SearchRepository — mock; при 5M DAU нужна реальная интеграция с OpenSearch и стратегия масштабирования (индексы, шарды, пулы).  
- Нет rate limiting и квот — риск перегрузки и злоупотреблений.  
- Ответ search: `{"hello": response}` — неочевидный контракт, лучше явный ключ (например `data` или корневой объект).

**Principal Architect (Oracle) #2**  
- В `global_exception_handler` в 500 отдаётся `detail=str(exc)` — утечка внутренней информации; в production должно быть общее сообщение + только trace_id.  
- CORS `*` в настройках по умолчанию недопустим для production.  
- Один worker в конфиге по умолчанию — недостаточно для высокой нагрузки.

**Principal Architect (Oracle) #3**  
- Нет circuit breaker и retry для внешних вызовов (когда репозиторий станет реальным).  
- Логирование в exception handlers: комментарии упоминают exc_info=True, но в коде его нет — при 503/500 в логах может не быть полного stack trace.  
- Нет разделения liveness и readiness (например, readiness с проверкой БД/поиска).

**Principal Research Engineer (Anthropic) #1**  
- Lazy injection стратегий в monitor через свойства — зависимость от глобального DI context при первом вызове; при тестах или альтернативном запуске возможны сюрпризы.  
- ProfilingMiddleware выполняет cProfile на каждый запрос при включённом профилировании — неприемлемо под нагрузкой 5M DAU.  
- Нет явной политики таймаутов для HTTP/поиска.

**Principal Research Engineer (Anthropic) #2**  
- FileHandler в logging без RotatingFileHandler в коде — rotation задаётся в config, но реализация handler может не поддерживать rotation (зависит от настроек dictConfig).  
- Метрики: только счётчики и гистограммы по event/status; нет метрик очередей, размера пула, ошибок по типам (по endpoint/методу).  
- Отсутствует документация по целевым SLO (latency, error rate) и runbooks.

**Principal Research Engineer (Anthropic) #3**  
- Нет кэширования (Redis/memcached) для частых запросов — при 5M DAU кэш ответов или результатов поиска критичен.  
- Контейнер приложения не входит в docker-compose с OpenSearch — нет одного команда для «всё поднять».  
- Дублирование зависимости granian в pyproject.toml (две строки с reload).

**Principal Architect (NASA) #1**  
- TrustedHostMiddleware с `allowed_hosts=["*"]` ослабляет защиту.  
- Нет явной политики секретов (например, только через переменные окружения или Vault в production).  
- Healthcheck не проверяет зависимые сервисы (поиск, БД) — только «приложение живое».

**Principal Architect (NASA) #2**  
- Жёсткая привязка Core (containers) к конкретным классам Infrastructure (StandardLoggingStrategy, SearchRepository) — для подмены всего стека нужны конфигурируемые фабрики.  
- Нет feature flags или механизма постепенного раската.  
- Makefile завязан на абсолютный VENV_PATH — снижает переносимость.

**Principal Architect (NASA) #3**  
- Нет backpressure и ограничения параллелизма на уровне приложения (только за счёт workers).  
- События (Events) и метрики не привязаны к SLO/алертам (нет примеров правил Prometheus/Alertmanager).  
- E2E тесты обращаются к эндпоинту `/v1/answer/generate`, но в application_api роуты подключены как `/v1` и `/common` без префикса `/api` — нужно проверить согласованность путей в документации и тестах.

---

## 4. Требования к исправлению (по членам комитета)

**Principal Architect (Oracle) #1**  
- Реализовать реальный SearchRepository с подключением к OpenSearch (из docker-compose), с таймаутами и ограничением размера ответа.  
- Ввести rate limiting (по IP или по ключу) на критические эндпоинты.  
- Изменить контракт ответа search на явный (например `{"data": response}` или `SearchResponse` в корне) и обновить тесты и документацию.

**Principal Architect (Oracle) #2**  
- В global_exception_handler не отдавать `str(exc)` в `detail`; использовать фиксированное сообщение (например из Reasons.internal_server_error.message) и только trace_id для поиска в логах.  
- Убрать CORS `*` в production-конфиге; задавать явный список origins.  
- Добавить в документацию и конфиг рекомендации по количеству workers и масштабированию (горизонтальное масштабирование за load balancer).

**Principal Architect (Oracle) #3**  
- Добавить `exc_info=True` в logger.error в infra_error_handler и global_exception_handler.  
- Реализовать readiness probe (например GET /common/ready), проверяющий доступность OpenSearch (и при необходимости БД).  
- Ввести обёртки вызовов внешних сервисов с circuit breaker и ограниченным retry (с экспоненциальной задержкой).

**Principal Research Engineer (Anthropic) #1**  
- Передавать стратегии observability в _MonitoringHandler явно (через конструктор/фабрику), а не через lazy resolve из DI, чтобы тесты и альтернативные точки входа не зависели от глобального контекста.  
- Профилирование отключать по умолчанию и не применять на каждый запрос в production; вынести в отдельный режим или sampling.  
- Задать таймауты для всех исходящих HTTP-вызовов и для поиска.

**Principal Research Engineer (Anthropic) #2**  
- Убедиться, что логи в файл пишутся через handler с rotation (например RotatingFileHandler или TimedRotatingFileHandler) в соответствии с LOGGING.ROTATION/RETENTION.  
- Расширить метрики: по endpoint, по методу, по коду ответа; рассмотреть метрики очереди запросов или активных запросов.  
- Описать в docs целевые SLO (p95 latency, error rate) и пример конфигурации алертов.

**Principal Research Engineer (Anthropic) #3**  
- Добавить слой кэширования для результатов поиска (или ключевых use case) с TTL и политикой инвалидации.  
- Включить сервис приложения в docker-compose рядом с OpenSearch и задать зависимость и сеть.  
- Удалить дубликат зависимости `granian[reload]` в pyproject.toml.

**Principal Architect (NASA) #1**  
- В production не использовать TrustedHostMiddleware с `*`; задавать явный список разрешённых host.  
- Задокументировать и применить политику секретов (например, только env или интеграция с Vault).  
- Расширить healthcheck: liveness — минимальная проверка процесса; readiness — проверка зависимостей (OpenSearch, при необходимости БД).

**Principal Architect (NASA) #2**  
- Вынести выбор реализаций (например, стратегии логирования, репозиторий) в конфиг или фабрики, чтобы можно было подменять реализации без правки containers.py.  
- Добавить механизм feature flags (конфиг или внешний сервис) для безопасного раската.  
- Сделать Makefile независимым от абсолютного VENV_PATH (например, через `uv run` или переменную из окружения).

**Principal Architect (NASA) #3**  
- Ввести ограничение параллельных запросов или очереди (например, semaphore на уровне приложения или за nginx).  
- Подготовить примеры правил алертов (Prometheus/Alertmanager) по метрикам и SLO.  
- Привести пути API к единому виду: либо везде с префиксом /api, либо без; обновить тесты и описание API.

---

## 5. Предложения по улучшению (по членам комитета)

**Principal Architect (Oracle) #1**  
- Описать в docs сценарий масштабирования: несколько инстансов за LB, shared-nothing, конфиг OpenSearch под шардирование.  
- Рассмотреть отдельный слой кэша (Redis) для сессий или горячих запросов.  
- Версионировать контракт API (уже есть v1) и описать политику обратной совместимости.

**Principal Architect (Oracle) #2**  
- Добавить структурированные логи (уже JSON) с обязательными полями: trace_id, span_id, timestamp, level, message, service.  
- Ввести метрику «время до первого байта» (TTFB) для ключевых эндпоинтов.  
- Настроить пример пайплайна деплоя (CI/CD) с прогоном тестов и линтеров.

**Principal Architect (Oracle) #3**  
- Добавить опциональный эндпоинт для сбора метрик профилирования (например, по запросу с заголовком или ключом) без влияния на все запросы.  
- Документировать runbook при падении OpenSearch или росте ошибок.  
- Рассмотреть распределённый трейсинг с sampling при высокой нагрузке.

**Principal Research Engineer (Anthropic) #1**  
- Вынести контракты API в OpenAPI и обеспечить генерацию клиентов или проверку контрактов в тестах.  
- Добавить тесты на граничные значения (пустой запрос, очень длинный запрос, спецсимволы) в search.  
- Рассмотреть использование async connection pool для OpenSearch.

**Principal Research Engineer (Anthropic) #2**  
- Добавить метрики потребления памяти и (при необходимости) GC.  
- Логировать агрегированную статистику сериализатора (например, раз в N минут) для выявления аномалий.  
- Ввести chaos-тесты (например, недоступность OpenSearch) и проверку восстановления.

**Principal Research Engineer (Anthropic) #3**  
- Подготовить helm chart или k8s манифесты для деплоя с настройкой replicas, ресурсов и probes.  
- Добавить интеграционный тест с реальным OpenSearch в CI (опционально, с пометкой integration).  
- Документировать порядок миграций индексов/схем поиска при изменении модели.

**Principal Architect (NASA) #1**  
- Ввести аудит критичных операций (логирование с уровнем audit при определённых действиях).  
- Рассмотреть mTLS или аутентификацию между сервисами при росте числа компонентов.  
- Документировать процедуру ротации секретов и сертификатов.

**Principal Architect (NASA) #2**  
- Добавить шаблон для нового use case (скрипт или cookiecutter): domain entity, interface, repository, service, endpoint, тесты.  
- Рассмотреть модульные контейнеры (отдельный контейнер для «поиск», «общее API») при дальнейшем росте.  
- В README указать минимальные и рекомендуемые ресурсы (CPU/RAM) для разных сценариев нагрузки.

**Principal Architect (NASA) #3**  
- Добавить метрики по количеству активных запросов (in-flight) по эндпоинтам.  
- Рассмотреть graceful shutdown с завершением текущих запросов и отключением от зависимостей.  
- Подготовить чек-лист pre-production (конфиг, секреты, лимиты, мониторинг, бэкапы).

---

## 6. Вердикт о принятии

**Итог голосования:**  
- **Условное принятие** (принятие с обязательными исправлениями).

**Условия для перехода в production при DAU 5M+:**

1. **Критично (блокеры):**  
   - Реализовать реальный SearchRepository с OpenSearch, таймаутами и лимитами.  
   - Убрать утечку внутренней информации в 500 ответе (`detail` не должен содержать `str(exc)`).  
   - Добавить `exc_info=True` в логирование при 503/500.  
   - Ввести rate limiting на публичные эндпоинты.  
   - Привести CORS и TrustedHost к безопасным значениям в production (не `*`).  
   - Реализовать readiness probe с проверкой зависимостей.

2. **Обязательно до высокой нагрузки:**  
   - Разделить liveness и readiness.  
   - Добавить кэширование для снижения нагрузки на поиск.  
   - Задать политику таймаутов и retry/circuit breaker для внешних вызовов.  
   - Уточнить и задокументировать контракт API (в т.ч. убрать обёртку `{"hello": response}` или формализовать её).  
   - Документировать SLO и примеры алертов.

3. **Рекомендуется:**  
   - Вынести выбор реализаций (стратегии, репозиторий) в конфиг/фабрики.  
   - Включить приложение в docker-compose с OpenSearch.  
   - Улучшить метрики (по endpoint, in-flight, ошибки).  
   - Сделать Makefile и пути API согласованными и переносимыми.

**Заключение:**  
Архитектура и качество кода создают хорошую основу для масштабирования, но в текущем виде сервис **не готов** к production с DAU 5M+ без реализации персистенции, защиты от перегрузки и исправления рисков безопасности и наблюдаемости. После выполнения критичных и обязательных пунктов комитет рекомендует повторную оценку и нагрузочное тестирование на целевом масштабе.
