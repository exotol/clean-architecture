my_project/
├── .venv/ # Виртуальное окружение
├── config/ # Папка для файлов конфигурации Dynaconf
│ ├── settings.toml # Базовые настройки
│ └── .secrets.toml # Секреты (в gitignore!)
├── src/
│ └── app/
│ ├── __init__.py
│ ├── main.py # Точка входа (FastAPI app)
│ ├── core/ # Ядро: конфиг, логгер, исключения
│ │ ├── config.py # Инициализация Dynaconf
│ │ ├── database.py # Подключение к БД (SQLAlchemy/AsyncPG)
│ │ └── exceptions.py
│ ├── api/ # HTTP слой (Роутеры)
│ │ ├── __init__.py
│ │ └── v1/ # Версионирование API
│ │ ├── router.py # Сборщик всех роутеров v1
│ │ └── endpoints/
│ │ └── users.py # Эндпоинты для юзеров
│ ├── schemas/ # Pydantic модели (DTO - Data Transfer Objects)
│ │ └── user.py # UserCreate, UserResponse
│ ├── models/ # ORM модели (таблицы БД)
│ │ └── user.py
│ ├── repositories/ # Слой доступа к данным (CRUD)
│ │ └── user.py
│ ├── services/ # Бизнес-логика (не знает про HTTP)
│ │ └── user.py
│ └── containers.py # (Опционально) DI контейнер или файл dependencies.py
├── tests/
├── Dockerfile
├── docker-compose.yml
├── alembic.ini # Миграции БД
├── pyproject.toml # Зависимости (uv / poetry)
└── README.md