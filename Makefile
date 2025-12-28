PYTHON_VERSION = 3.12
VENV_PATH = /home/v0id/main/01_projects/venv/eva
# Указываем, что используем bash (по умолчанию make часто использует sh)
SHELL := /bin/bash
.PHONY: install.dep.python install.uv venv.create sync

install.dep.python:
	@echo "Установить зависимости для сборки питона"
	sudo apt update
	sudo apt install -y make build-essential libssl-dev zlib1g-dev \
	libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev \
	libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev git


install.pyenv:
	@echo "Установка pyenv..."
	# Явно указываем скрипту установки, куда ставить, используя $(HOME)
	export PYENV_ROOT="$(HOME)/.pyenv"; \
#	curl https://pyenv.run | bash

	@echo "Настройка .bashrc..."
	# Используем $(HOME) для путей к файлам. Это гарантирует, что Make подставит верный путь.
	# Внутри echo мы оставляем $$HOME, чтобы в сам файл записалась переменная $HOME (для переносимости),
	# либо можно тоже заменить на $(HOME), если хотите захардкодить путь.

	grep -q "PYENV_ROOT" "$(HOME)/.bashrc" || echo 'export PYENV_ROOT="$$HOME/.pyenv"' >> "$(HOME)/.bashrc"
	grep -q "PYENV_ROOT/bin" "$(HOME)/.bashrc" || echo '[[ -d $$PYENV_ROOT/bin ]] && export PATH="$$PYENV_ROOT/bin:$$PATH"' >> "$(HOME)/.bashrc"
	grep -q "pyenv init" "$(HOME)/.bashrc" || echo 'eval "$$(pyenv init - bash)"' >> "$(HOME)/.bashrc"
	grep -q "pyenv virtualenv" "$(HOME)/.bashrc" || echo 'eval "$$(pyenv virtualenv-init -)"' >> "$(HOME)/.bashrc"
	@echo "-----------------------------------------------------------"
	@echo "Установка завершена в $(HOME)/.pyenv"
	@echo "Выполните 'source ~/.bashrc' вручную."

install.python:
	@echo "Установка питона: $(PYTHON_VERSION)"
	#uv python install $(PYTHON_VERSION)
	pyenv install $(PYTHON_VERSION)

create.venv:
	@echo "Создать виртуальное окружение: $(PYTHON_VENV)"
	pyenv virtualenv $(PYTHON_VERSION) $(PYTHON_VENV)
	pyenv local $(PYTHON_VENV)

remove.venv:
	@echo "Удалить виртуальное окржуение: $(PYTHON_VENV)"
	pyenv virtualenv-delete $(PYTHON_VENV)

install.uv:
	@echo "Установка uv"
	curl -LsSf https://astral.sh/uv/install.sh | sh

install.direnv:
	@echo "Установка direnv в ~/.local/bin"
	@mkdir -p ~/.local/bin
	export bin_path=~/.local/bin && curl -sfL https://direnv.net/install.sh | bash
	@echo "-----------------------------------------------------------"
	@echo "direnv установлен. Убедитесь, что ~/.local/bin в PATH"
	@echo "Выполните 'make setup.direnv' для настройки хука bash"

setup.direnv:
	@echo "Настройка direnv hook в ~/.bashrc"
	@grep -q 'eval "$$(direnv hook bash)"' ~/.bashrc || echo 'eval "$$(direnv hook bash)"' >> ~/.bashrc
	@echo "Настройка отображения имени окружения в prompt"
	@grep -q 'show_virtual_env' ~/.bashrc || cat >> ~/.bashrc << 'EOF'

	# Показывать имя виртуального окружения в prompt (для direnv)
	# Проверка VIRTUAL_ENV_DISABLE_PROMPT предотвращает дублирование в IDE (PyCharm)
	show_virtual_env() {
		if [[ -n "$$VIRTUAL_ENV" && -z "$$VIRTUAL_ENV_DISABLE_PROMPT" ]]; then
			echo "$$(basename "$$VIRTUAL_ENV") "
		fi
	}
	export -f show_virtual_env
	PS1='$$(show_virtual_env)'"$$PS1"
	EOF
	@echo "Разрешение .envrc в проекте"
	direnv allow
	@echo "-----------------------------------------------------------"
	@echo "Готово! Выполните 'source ~/.bashrc' или откройте новый терминал"

venv.create:
	@echo "Создать виртуальное окружение в $(VENV_PATH)"
	uv venv $(VENV_PATH) --python $(PYTHON_VERSION)
	@echo "Окружение создано. Выполните 'direnv allow' для автоактивации."

sync.uv:
	@echo "Синхронизация зависимостей"
	uv sync

init.uv:
	@echo "Инициализация проекта (если нет pyproject.toml)"
	uv init

ruff.check:
	@echo "Запустить проверку RUFF качества кода"
	uv run ruff check . --fix --unsafe-fixes

ruff.format:
	@echo "Запустить форматирование с помощью ruff"
	uv run ruff format .

mypy.check:
	@echo "Запустить проверку MYPY типизации"
	uv run mypy --install-types --non-interactive .

install.pre-commit:
	@echo "Установить сконфигрурированные пре-коммит хуки"
	uv run pre-commit install

remove.pre-commit:
	@echo "Удалить сконфигрурированные пре-коммит хуки"
	uv run pre-commit uninstall

wemake.run:
	@echo "Запуск wemake"
	uv run flake8 . --select=WPS




##########################

start.infra:
	@echo "Запустить инфраструктуру"
	sudo docker compose --file docker/docker-compose.yml up

check.opensearch:
	@echo "Проверить доступность опенсерча с дефолтным паролем"
	# Флаг -k (insecure) нужен, так как сертификаты самоподписанные
	curl -X GET https://localhost:9200 -u 'admin:myStrongPassword123!' -k

block.off.index:
	@echo "Убрать блокировку индекса на запись"
	curl -X PUT "https://localhost:9200/_all/_settings" \
		-u 'admin:myStrongPassword123!' -k \
		-H 'Content-Type: application/json' \
		-d'{"index.blocks.read_only_allow_delete": null}'


run.pytest:
	@echo "Запуск pytest"
	pytest tests

run.load:
	@echo "Запуск нагрузочного тестирования (Locust)"
	# Запуск Locust. Можно передать параметры через ARGS, например: make run.load ARGS="--headless -u 10 -r 2 -t 30s"
	uv run locust -f tests/performance/locustfile.py $(ARGS)


profile.view:
	@echo "Просмотр последнего профиля в snakeviz"
	@if [ -z "$$(ls -A profiles/*.prof 2>/dev/null)" ]; then echo "Нет профилей в profiles/"; exit 1; fi
	snakeviz $$(ls -t profiles/*.prof | head -1)

profile.clean:
	@echo "Удаление всех профилей"
	rm -rf profiles/*.prof
	@echo "Профили удалены"

profile.speedscope.view:
	@echo "Конвертация последнего профиля в speedscope формат"
	@if [ -z "$$(ls -A profiles/*.prof 2>/dev/null)" ]; then echo "Нет профилей в profiles/"; exit 1; fi
	@LATEST=$$(ls -t profiles/*.prof | head -1); \
	python3 scripts/prof_to_speedscope.py "$$LATEST"

##########################
# Docker
##########################

DOCKER_IMAGE ?= eva
DOCKER_TAG ?= latest

docker.build:
	@echo "Сборка Docker образа $(DOCKER_IMAGE):$(DOCKER_TAG)"
	docker build -f docker/Dockerfile -t $(DOCKER_IMAGE):$(DOCKER_TAG) .

docker.build.no-cache:
	@echo "Сборка Docker образа без кеша"
	docker build -f docker/Dockerfile -t $(DOCKER_IMAGE):$(DOCKER_TAG) --no-cache .

docker.run:
	@echo "Запуск контейнера $(DOCKER_IMAGE):$(DOCKER_TAG)"
	docker run --rm -p 8000:8000 --name eva-app $(DOCKER_IMAGE):$(DOCKER_TAG)

docker.run.detached:
	@echo "Запуск контейнера в фоновом режиме"
	docker run -d -p 8000:8000 --name eva-app $(DOCKER_IMAGE):$(DOCKER_TAG)
	@echo "Контейнер запущен. Остановить: docker stop eva-app"

docker.stop:
	@echo "Остановка контейнера"
	docker stop eva-app || true
	docker rm eva-app || true

docker.logs:
	@echo "Логи контейнера"
	docker logs -f eva-app

docker.shell:
	@echo "Запуск shell в контейнере"
	docker run --rm -it $(DOCKER_IMAGE):$(DOCKER_TAG) /bin/bash

docker.size:
	@echo "Размер Docker образа"
	docker images $(DOCKER_IMAGE):$(DOCKER_TAG) --format "{{.Repository}}:{{.Tag}} - {{.Size}}"

docker.clean:
	@echo "Удаление Docker образа"
	docker rmi $(DOCKER_IMAGE):$(DOCKER_TAG) || true

