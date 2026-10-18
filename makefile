.PHONY: up down test test-unit test-selenium selenium-up selenium-down logs test-log app-log test-unit-log migration

SHELL := /bin/bash
.SHELLFLAGS := -o pipefail -c

up:
	docker compose --profile dev up -d

down:
	docker compose --profile dev down

test-unit:
	docker compose exec app pytest -m "not selenium" -v

test-file:
	docker compose exec app pytest $(FILE) -v

test-selenium:
	docker compose -f docker-compose.yml -f docker-compose.selenium.yml --profile dev up -d
	docker compose -f docker-compose.yml -f docker-compose.selenium.yml up -d --force-recreate app selenium
	docker compose -f docker-compose.yml -f docker-compose.selenium.yml exec app pytest -m selenium -v
	docker compose up -d --force-recreate app

selenium-up:
	docker compose --profile dev up -d
	docker compose --profile dev -f docker-compose.yml -f docker-compose.selenium.yml up -d --force-recreate app

selenium-down:
	docker compose up -d --force-recreate app

test: test-unit test-selenium

logs:
	docker compose logs -f app

test-unit-log:
	docker compose logs -f app > docs/console_log.txt 2>&1 & \
	LOG_PID=$$!; \
	$(MAKE) test-unit 2>&1 | tee docs/console_tests_log.txt; \
	EXIT_CODE=$${PIPESTATUS[0]}; \
	sleep 2; \
	kill $$LOG_PID 2>/dev/null || true; \
	exit $$EXIT_CODE

test-log:
	docker compose logs -f app > docs/console_log.txt 2>&1 & \
	LOG_PID=$$!; \
	$(MAKE) test-selenium 2>&1 | tee docs/console_tests_log.txt; \
	EXIT_CODE=$${PIPESTATUS[0]}; \
	sleep 2; \
	kill $$LOG_PID 2>/dev/null || true; \
	exit $$EXIT_CODE

app-log:
	timeout $(TEMPO) docker compose logs -f app 2>&1 | tee docs/console_log.txt || true

cria-user-cli:
	docker compose exec -w /app/src app python -m app.cli.criar_admin

cria-paroquia-cli:
	docker compose exec -w /app/src app python -m app.cli.criar_paroquia
	
code-format-check:
	docker compose exec app poetry run ruff format src/
	docker compose exec app poetry run ruff check --fix src/

migration:
	@if [ -z "$(msg)" ]; then \
		echo "Uso: make migration msg=\"mensagem da migração\""; \
		exit 1; \
	fi
	docker compose exec app alembic revision --autogenerate -m "$(msg)"

migrate:
	docker compose exec app alembic upgrade head
