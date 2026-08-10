#!/usr/bin/env bash
#
# Add a per-language testing worker.
#
# The intended topology is one worker image per language. Wiring one up by hand
# means touching five places that must agree and that nothing cross-checks: a
# token in .env, a service in a deployment file, a container in compose, a
# runtime in the image, and the executionBackend in every example's meta.yaml.
# This script does the first two (the mechanical, easy-to-typo ones) and prints
# the compose block for the third.
#
# Usage:
#   scripts/add-testing-language.sh <language> [--queue <name>] [--slug <slug>]
#
# Example:
#   scripts/add-testing-language.sh octave
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${REPO_ROOT}/.env"
DEPLOY_DIR="${REPO_ROOT}/data/deployments"

RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'; NC=$'\033[0m'

# Languages the shared testing image can actually provide. MATLAB is excluded on
# purpose: it is a separate image with its own entrypoint, so it is not something
# this script can wire up.
SUPPORTED="python octave r julia c cpp fortran document"

usage() { sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

[[ $# -ge 1 ]] || usage
LANGUAGE="$(printf '%s' "$1" | tr '[:upper:]' '[:lower:]')"; shift
QUEUE=""; SLUG=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --queue) QUEUE="$2"; shift 2 ;;
    --slug)  SLUG="$2";  shift 2 ;;
    *) echo "${RED}Unknown option: $1${NC}"; usage ;;
  esac
done

if [[ "$LANGUAGE" == "matlab" ]]; then
  echo "${RED}MATLAB is not wired up by this script.${NC}"
  echo "It runs in its own image (docker/temporal-worker-matlab) with a licensed"
  echo "engine; see ops/docker/docker-compose.matlab.yaml."
  exit 1
fi

if ! printf '%s\n' $SUPPORTED | grep -qx "$LANGUAGE"; then
  echo "${RED}Unsupported language '${LANGUAGE}'.${NC} The testing image provides: ${SUPPORTED}"
  exit 1
fi

# Defaults follow the convention the backend derives queues from, so leaving
# task_queue unset in the service config would resolve to the same name.
[[ -n "$QUEUE" ]] || QUEUE="testing-${LANGUAGE}"
[[ -n "$SLUG"  ]] || SLUG="itpcp.exec.${LANGUAGE}"

LANG_UPPER="$(printf '%s' "$LANGUAGE" | tr '[:lower:]' '[:upper:]')"
TOKEN_VAR="TESTING_WORKER_TOKEN_${LANG_UPPER}"
DEPLOY_FILE="${DEPLOY_DIR}/testing-worker-${LANGUAGE}.yaml"

[[ -f "$ENV_FILE" ]] || { echo "${RED}No .env at ${ENV_FILE}${NC} — run ./setup-env.sh first."; exit 1; }

if [[ -f "$DEPLOY_FILE" ]]; then
  echo "${YELLOW}${DEPLOY_FILE} already exists — leaving it alone.${NC}"
else
  # Same shape setup-env.sh uses: ctp_ + 32 url-safe base64 chars. Must satisfy
  # utils/api_token.validate_token_format or every request 401s.
  rnd=$(openssl rand -base64 24 2>/dev/null || head -c 24 /dev/urandom | base64)
  rnd=$(printf '%s' "$rnd" | tr '+/' '-_' | tr -d '=\n\r' | cut -c1-32)
  TOKEN="ctp_${rnd}"

  if grep -q "^${TOKEN_VAR}=" "$ENV_FILE"; then
    echo "${YELLOW}${TOKEN_VAR} already in .env — reusing it.${NC}"
  else
    printf '\n# Testing worker token for %s (added by scripts/add-testing-language.sh)\n%s="%s"\n' \
      "$LANGUAGE" "$TOKEN_VAR" "$TOKEN" >> "$ENV_FILE"
    echo "${GREEN}✓${NC} Added ${TOKEN_VAR} to .env"
  fi

  mkdir -p "$DEPLOY_DIR"
  cat > "$DEPLOY_FILE" <<YAML
# Testing worker for ${LANGUAGE}. Applied idempotently on every API start by
# business_logic/bootstrap.py:ensure_bootstrap_services.
services:
  - slug: ${SLUG}                 # must equal properties.executionBackend.slug
                                  # in the meta.yaml of ${LANGUAGE} examples
    service_type_path: testing.temporal
    language: ${LANGUAGE}         # selects the runner AND, by default, the queue
    description: ${LANGUAGE} testing worker
    user:
      email: testing-worker-${LANGUAGE}@computor.local
      given_name: Testing
      family_name: Worker ${LANGUAGE}
    api_token:
      token: \${${TOKEN_VAR}}
      name: Testing Worker Token (${LANGUAGE})
      # Omit expires_days for a token that never expires. If you set one, note
      # that expiry is a hard cutoff: the worker stops authenticating and every
      # test fails. Startup warns for the last 30 days.
    config:
      temporal:
        task_queue: ${QUEUE}      # must equal the container's --queues value
YAML
  echo "${GREEN}✓${NC} Wrote ${DEPLOY_FILE#$REPO_ROOT/}"
fi

cat <<EOF

${YELLOW}Add this service to ops/docker/docker-compose.dev.yaml (and .prod.yaml):${NC}

  temporal-worker-testing-${LANGUAGE}:
    build:
      context: ../../
      dockerfile: ./docker/temporal-worker-testing/Dockerfile
    networks:
      - computor-network
    restart: unless-stopped
    stop_grace_period: 330s
    security_opt:
      - "no-new-privileges:true"
    command: ["--queues=${QUEUE}"]
    extra_hosts:
      - "host.docker.internal:host-gateway"
    environment:
      - TZ=UTC
      - RUNNING_IN_DOCKER=true
      - TEMPORAL_HOST=temporal
      - TEMPORAL_PORT=7233
      - TEMPORAL_NAMESPACE=default
      - API_URL=\${API_URL}
      - API_TOKEN=\${${TOKEN_VAR}:?set ${TOKEN_VAR} in .env}
      - TESTING_EXECUTABLE=computor-test
    depends_on:
      - temporal
      - postgres
      - redis

${YELLOW}Then:${NC}
  1. restart the API so bootstrap creates the service + token
  2. ./computor.sh up   (builds and starts the new worker)
  3. point ${LANGUAGE} examples at it in meta.yaml:
         properties:
           executionBackend:
             slug: ${SLUG}

The worker refuses to start if the image cannot provide '${LANGUAGE}', and
POST /tests refuses a service whose queue has no listening worker — so a
half-finished wiring fails loudly instead of hanging.
EOF
