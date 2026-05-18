SHELL := /bin/bash
COMPOSE := docker compose -f infra/docker-compose.yml --env-file .env

.PHONY: env up down logs ps migrate seed ingest api web fmt

env:
	@[ -f .env ] || (cp .env.example .env && echo "created .env — fill in API keys")

up: env
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=200

ps:
	$(COMPOSE) ps

# Migrations auto-run on first DB boot via /docker-entrypoint-initdb.d.
# Use this only to re-run after schema edits (drops the volume — destructive!).
migrate-reset:
	$(COMPOSE) down -v
	$(COMPOSE) up -d db
	@echo "DB re-initialized with latest migrations."

# Seed countries from Natural Earth (admin-0) into regions.
seed:
	$(COMPOSE) exec api python -m scripts.seed_regions

ingest:
	$(COMPOSE) exec api python -m ingestion.run_all

api:
	$(COMPOSE) exec api bash

web:
	$(COMPOSE) exec web sh

fmt:
	$(COMPOSE) exec api ruff format api ingestion simulator optimizer agent || true
