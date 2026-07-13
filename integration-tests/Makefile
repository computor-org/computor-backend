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

.PHONY: help env stage-realm up wait down clean logs ps test shell-api

help:
	@echo "Targets:"
	@echo "  env         Copy .env.integration.template -> .env.integration + stage Keycloak realm"
	@echo "  stage-realm Regenerate keycloak-import/ from data/keycloak/computor-realm.json"
	@echo "  up          Build, start, wait for health"
	@echo "  wait        Wait for all services to be healthy"
	@echo "  test        Run the pytest suite against the running stack"
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

# Stage the Keycloak realm into the import dir the keycloak container bind-mounts,
# substituting the client secrets from .env.integration for the JSON placeholders.
# Keycloak imports it ONLY on a fresh keycloak-db volume, so re-run `make clean`
# after changing a secret.
stage-realm:
	@set -a; . ./.env.integration; set +a; \
	mkdir -p keycloak-import; \
	sed -e "s|PLACEHOLDER_CLIENT_SECRET|$${KEYCLOAK_CLIENT_SECRET}|g" \
	    -e "s|PLACEHOLDER_FORGEJO_CLIENT_SECRET|$${FORGEJO_CLIENT_SECRET}|g" \
	    ../data/keycloak/computor-realm.json > keycloak-import/computor-realm.json; \
	echo "Staged Keycloak realm → keycloak-import/computor-realm.json"

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

shell-api:
	$(COMPOSE) exec api bash
