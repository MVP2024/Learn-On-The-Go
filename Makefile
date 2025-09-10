# Makefile для удобной разработки

.PHONY: build up down logs shell migrate fixtures test-local test-docker test-docker-run

build:
	docker compose build

up:
	docker compose up -d --build

down:
	docker compose down -v

logs:
	docker compose logs -f web

shell:
	docker compose exec web /bin/bash

migrate:
	docker compose exec web python manage.py migrate

fixtures:
	docker compose exec web python utils/clear_and_load_fixtures.py --yes

# Запуск тестов локально (в .venv)
test-local:
	@echo "Running pytest locally (use your .venv)"
	pytest -q -o addopts=''

# Быстрый запуск тестов в контейнере (использует config.test_settings)
test-docker-run:
	# Использует docker compose run чтобы явным образом передать переменные окружения
	docker compose run --rm -e DJANGO_SETTINGS_MODULE=config.test_settings web python -m pytest -q -o addopts=''

# Полный путь: поднять сервисы и запустить pytest внутри web
test-docker:
	docker compose up -d --build db redis
	# запускаем тесты внутри web контейнера с тестовыми настройками
	docker compose exec -e DJANGO_SETTINGS_MODULE=config.test_settings web /bin/bash -lc "python -m pytest -q -o addopts=''"
