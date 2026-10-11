.PHONY: up down test test-unit test-selenium selenium-up selenium-down logs

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

# Garante que TODA a stack dev (incluindo "selenium") está de pé,
# e recria SÓ o app com o override do banco _test.
selenium-up:
	docker compose --profile dev up -d
	docker compose --profile dev -f docker-compose.yml -f docker-compose.selenium.yml up -d --force-recreate app

selenium-down:
	docker compose up -d --force-recreate app

test: test-unit test-selenium

logs:
	docker compose logs -f app

cria-user-cli:
	docker compose exec -w /app/src app python -m app.cli.criar_admin

migrate:
	docker compose exec app alembic upgrade head

code-format-check:
	docker compose exec app poetry run ruff format src/
	docker compose exec app poetry run ruff check --fix src/
