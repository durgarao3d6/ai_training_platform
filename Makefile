# Thin wrappers around docker compose. Needs only Docker (and make, or use scripts/dev.ps1).
BASE  := --env-file .env -f infra/compose.yml
DEV   := $(BASE) -f infra/compose.dev.yml
TEST  := $(BASE) -f infra/compose.test.yml
TOOLS := docker compose $(TEST) --profile tools run --rm --no-deps tools

.PHONY: up down test test-integration lint migrate seed content-validate client a11y reset

up:
	@test -f .env || cp .env.example .env
	docker compose $(DEV) up --build -d --wait

down:
	docker compose $(DEV) down

test:
	$(TOOLS) sh -c "cd apps/api && python -m pytest -q"

test-integration:
	docker compose $(TEST) up -d --wait s3
	$(TOOLS) sh -c "cd apps/api && RUN_INTEGRATION=1 python -m pytest -q tests/integration"

lint:
	$(TOOLS) sh -c "ruff check apps services && ruff format --check apps services && cd apps/api && mypy app tests"
	docker compose $(DEV) run --rm --no-deps web sh -c "npm run lint && npm run typecheck"

migrate:
	docker compose $(DEV) run --rm api alembic upgrade head

seed:
	docker compose $(DEV) run --rm api python -m app.seed.bootstrap

content-validate:
	$(TOOLS) sh -c "cd apps/api && python -m app.content.cli validate /work/content"

client:
	$(TOOLS) sh -c "cd apps/api && python -m app.api.export_openapi && openapi-typescript /work/packages/contracts/openapi.json -o /work/packages/contracts/client/schema.d.ts && cp /work/packages/contracts/client/schema.d.ts /work/apps/web/lib/api-schema.d.ts"

a11y:
	@echo "Not implemented yet: task 2.4 onwards (Playwright + axe)"; exit 1

reset:
	docker compose $(DEV) down -v
	$(MAKE) up
