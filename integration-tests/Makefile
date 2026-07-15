# Integration-test stack control.
#
# Typical session:
#   make env        # one-time: copies .env.integration.template -> .env.integration
#   make up         # builds + starts + waits for health
#   make test       # runs pytest against the live stack
#   make down       # stops containers (keeps volumes)
#   make clean      # stops containers and wipes volumes

SHELL := /usr/bin/env bash
COMPOSE := docker compose -f docker-compose.integration.yaml --env-file .env.integration
PYTEST := pytest

.PHONY: help env stage-realm up wait down clean logs ps test report shell-api

help:
	@echo "Targets:"
	@echo "  env         Copy .env.integration.template -> .env.integration + stage Keycloak realm"
	@echo "  stage-realm Regenerate keycloak-import/ from data/keycloak/computor-realm.json"
	@echo "  up          Build, start, wait for health"
	@echo "  wait        Wait for all services to be healthy"
	@echo "  test        Run the pytest suite against the running stack"
	@echo "  report      Run the suite and regenerate reports/latest.md"
	@echo "  logs        Tail all service logs"
	@echo "  ps          Show container status"
	@echo "  down        Stop containers (preserves volumes)"
	@echo "  clean       Stop containers and remove volumes (realm re-imports on next up)"
	@echo "  shell-api   Shell into the API container"

env:
	@if [ ! -f .env.integration ]; then \
		cp .env.integration.template .env.integration; \
		echo "Created .env.integration — edit if host ports need changing."; \
	else \
		echo ".env.integration already exists."; \
	fi
	@$(MAKE) stage-realm

# Stage the Keycloak realm into the import dir the keycloak container bind-mounts:
# sets the client secrets and adds the integration API callback to the
# computor-backend client (see scripts/stage_realm.py). Keycloak imports it ONLY
# on a fresh keycloak-db volume, so re-run `make clean` after changing a secret.
PYTHON ?= $(shell [ -x ../.venv/bin/python ] && echo ../.venv/bin/python || echo python3)
stage-realm:
	@set -a; . ./.env.integration; set +a; \
	$(PYTHON) scripts/stage_realm.py ../data/keycloak/computor-realm.json keycloak-import/computor-realm.json

up: env
	$(COMPOSE) up -d --build
	$(MAKE) wait

wait:
	./scripts/wait_for_services.sh

down:
	$(COMPOSE) down

clean:
	$(COMPOSE) down -v --remove-orphans

logs:
	$(COMPOSE) logs -f --tail=200

ps:
	$(COMPOSE) ps

test:
	$(PYTEST)

# Run the suite and surface the markdown report. reporting.py writes
# reports/latest.md at session finish; a committed sample lives in
# reports/example.md. The `-` lets the echo run even when tests fail.
report:
	-$(PYTEST)
	@echo "📝 Report → reports/latest.md (committed sample: reports/example.md)"

shell-api:
	$(COMPOSE) exec api bash
