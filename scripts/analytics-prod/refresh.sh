#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

if [ ! -f .env ]; then
    echo ".env not found" >&2
    exit 1
fi

set -a
# shellcheck disable=SC1091
. ./.env
set +a

: "${ANALYTICS_SOURCE_DATABASE_URL:?must be set in .env}"
: "${ANALYTICS_REFRESH_COURSE_ID:?must be set in .env}"

if [ "${ANALYTICS_SOURCE_TUNNEL_ENABLED:-false}" = "true" ]; then
    scripts/analytics-prod/source-tunnel.sh ensure
fi

if [ "${PUBLIC_DOMAIN:-}" != "" ]; then
    PUBLIC_DOMAIN="${PUBLIC_DOMAIN%/}"
    public_host="${PUBLIC_DOMAIN#*://}"
    public_host="${public_host%%/*}"
    export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-${PUBLIC_DOMAIN}/api}"
    export KEYCLOAK_PUBLIC_URL="${KEYCLOAK_PUBLIC_URL:-${PUBLIC_DOMAIN}/auth}"
    export FORGEJO_ROOT_URL="${FORGEJO_ROOT_URL:-${PUBLIC_DOMAIN}/forgejo}"
    export FORGEJO_DOMAIN="${FORGEJO_DOMAIN:-$public_host}"
fi

if [ "${CODER_ENABLED:-false}" = "true" ]; then
    export POSTGRES_MULTIPLE_DATABASES="computor,coder"
else
    export POSTGRES_MULTIPLE_DATABASES="computor"
fi

if [ -z "${DOCKER_GID:-}" ]; then
    DOCKER_GID="$(getent group docker | cut -d: -f3 2>/dev/null || stat -c '%g' /var/run/docker.sock 2>/dev/null || true)"
    export DOCKER_GID
fi

compose_files=(
    -f ops/docker/docker-compose.base.yaml
    -f ops/docker/docker-compose.prod.yaml
    -f ops/docker/docker-compose.web.yaml
)

if [ "${CODER_ENABLED:-false}" = "true" ]; then
    compose_files+=(-f ops/docker/docker-compose.coder.yaml)
fi
if [ "${KEYCLOAK_ENABLED:-false}" = "true" ]; then
    compose_files+=(-f ops/docker/docker-compose.keycloak.yaml)
    compose_files+=(-f ops/docker/docker-compose.keycloak-prod.yaml)
fi
if [ "${GIT_SERVER:-}" = "forgejo" ]; then
    compose_files+=(-f ops/docker/docker-compose.forgejo.yaml)
fi
if [ "${GIT_SERVER:-}" = "forgejo" ] && [ "${KEYCLOAK_ENABLED:-false}" = "true" ]; then
    compose_files+=(-f ops/docker/docker-compose.forgejo-keycloak.yaml)
fi
if [ "${MATLAB_ENABLED:-false}" = "true" ]; then
    compose_files+=(-f ops/docker/docker-compose.matlab.yaml)
fi

docker compose "${compose_files[@]}" config --quiet
docker compose "${compose_files[@]}" up -d analytics-permissions

docker compose "${compose_files[@]}" run --rm --no-deps \
    uvicorn python -m computor_backend.scripts.analytics_refresh
