.PHONY: help up down build logs migrate migrate-create migrate-history migrate-downgrade db-stamp db-reset

help:
	@echo "reNgine 3.0 Dev Commands"
	@echo ""
	@echo "  Docker:"
	@echo "    make up              Start all services"
	@echo "    make down            Stop all services"
	@echo "    make build           Rebuild all containers"
	@echo "    make logs            Tail all logs"
	@echo "    make logs-api        Tail API logs"
	@echo "    make logs-worker     Tail worker logs"
	@echo ""
	@echo "  Database Migrations:"
	@echo "    make migrate                  Apply all pending migrations"
	@echo "    make migrate-create m=msg     Create new migration (autogenerate)"
	@echo "    make migrate-history          Show migration history"
	@echo "    make migrate-downgrade        Rollback last migration"
	@echo "    make db-stamp                 Stamp DB as current (existing DB setup)"
	@echo "    make db-reset                 Drop all tables and re-migrate (DESTRUCTIVE)"
	@echo ""
	@echo "  Debug:"
	@echo "    make shell-api       Shell into API container"
	@echo "    make shell-worker    Shell into worker container"
	@echo "    make db-shell        PostgreSQL shell"

# Docker
up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

logs-api:
	docker compose logs -f api

logs-worker:
	docker compose logs -f worker-default

migrate:
	docker compose exec api uv run alembic upgrade head

migrate-create:
	@if [ -z "$(m)" ]; then echo "Usage: make migrate-create m='migration message'"; exit 1; fi
	docker compose exec api uv run alembic revision --autogenerate -m "$(m)"

migrate-history:
	docker compose exec api uv run alembic history --verbose

migrate-downgrade:
	docker compose exec api uv run alembic downgrade -1

db-stamp:
	docker compose exec api uv run alembic stamp head

db-reset:
	@echo "WARNING: This will drop all tables and re-migrate!"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	docker compose exec api uv run alembic downgrade base
	docker compose exec api uv run alembic upgrade head

# Shells
shell-api:
	docker compose exec api bash

shell-worker:
	docker compose exec worker-default bash

db-shell:
	docker compose exec db psql -U rengine -d rengine
