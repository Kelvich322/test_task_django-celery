.PHONY: up down up-build down-clean restart lint test

up:
	docker compose up

down:
	docker compose down

up-build:
	docker compose up --build

down-clean:
	docker compose down -v --remove-orphans

restart:
	docker compose restart

lint:
	uv run ruff format .
	uv run ruff check --fix .

test:
	pytest -v