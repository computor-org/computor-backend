#!/bin/bash
#
# Shared library for the computor lifecycle CLI (computor.sh) and the
# legacy wrapper scripts. Functions only — sourcing this file has no side
# effects. Every consumer of the compose stack (up/down/status/maintenance/
# update, wipe/align helpers) must get its .env loading, public-URL
# derivation and COMPOSE_FILES assembly from here so the feature-flag →
# overlay mapping exists in exactly one place.

# Guard against double-sourcing (computor.sh sources common.sh and update.sh,
# which may itself need common.sh).
[ -n "${_COMPUTOR_COMMON_SOURCED:-}" ] && return 0
_COMPUTOR_COMMON_SOURCED=1

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Repo root, independent of the caller's cwd (also correct inside the updater
# container, where the repo is bind-mounted at its host path).
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OPS_DIR="${REPO_ROOT}/ops"

log()  { echo -e "$@"; }
warn() { echo -e "${YELLOW}$*${NC}"; }
die()  { echo -e "${RED}$*${NC}" >&2; exit 1; }

# Load .env from the repo root (the only env file the runtime scripts read).
load_env() {
    [ -f "${REPO_ROOT}/.env" ] || die "No .env file found in ${REPO_ROOT}!
Please create a .env file with your configuration (see ./setup-env.sh)."
    set -a
    # shellcheck disable=SC1091
    source "${REPO_ROOT}/.env"
    set +a
}

# In production, PUBLIC_DOMAIN is the single source of truth for the public
# URLs. Each uses ${VAR:-...}, so an explicitly-set value in .env still wins
# (per-service override). Dev is untouched: PUBLIC_DOMAIN is empty there.
# Needed by `down` too: docker-compose.prod.yaml uses ${NEXT_PUBLIC_API_URL:?},
# so without this even stopping the stack fails interpolation.
derive_public_urls() {
    local environment="$1"
    if [ "$environment" = "prod" ] && [ -n "${PUBLIC_DOMAIN:-}" ]; then
        PUBLIC_DOMAIN="${PUBLIC_DOMAIN%/}"            # tolerate a trailing slash
        local _pd_host="${PUBLIC_DOMAIN#*://}"; _pd_host="${_pd_host%%/*}"
        export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-${PUBLIC_DOMAIN}/api}"
        export KEYCLOAK_PUBLIC_URL="${KEYCLOAK_PUBLIC_URL:-${PUBLIC_DOMAIN}/auth}"
        export FORGEJO_ROOT_URL="${FORGEJO_ROOT_URL:-${PUBLIC_DOMAIN}/forgejo}"
        export FORGEJO_DOMAIN="${FORGEJO_DOMAIN:-${_pd_host}}"
    fi
}

# Pin the Compose project name. The base compose file also declares
# `name: computor` (the canonical source); exporting keeps the name stable
# even for ad-hoc `docker compose` calls. An explicit value in .env wins.
pin_project_name() {
    export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-computor}"
}

# The one true feature-flag → compose-overlay mapping. Sets COMPOSE_FILES.
# Detection flags (*_DETECTED, set by detect_environment for `down` on a
# stack whose .env has since changed) act as OR-inputs to the .env flags.
# Silent: callers wanting a human summary use print_stack_summary.
assemble_compose_files() {
    local environment="$1"
    local d="${OPS_DIR}/docker"

    COMPOSE_FILES="-f ${d}/docker-compose.base.yaml -f ${d}/docker-compose.${environment}.yaml"

    # Web frontend container exists in production only (dev runs `next dev` on the host)
    if [ "$environment" = "prod" ]; then
        COMPOSE_FILES="$COMPOSE_FILES -f ${d}/docker-compose.web.yaml"
    fi

    if [ "${CODER_ENABLED:-}" = "true" ] || [ "${CODER_DETECTED:-}" = "true" ]; then
        COMPOSE_FILES="$COMPOSE_FILES -f ${d}/docker-compose.coder.yaml"
        export POSTGRES_MULTIPLE_DATABASES="computor,coder"
    else
        export POSTGRES_MULTIPLE_DATABASES="computor"
    fi

    if [ "${KEYCLOAK_ENABLED:-}" = "true" ] || [ "${KEYCLOAK_DETECTED:-}" = "true" ]; then
        COMPOSE_FILES="$COMPOSE_FILES -f ${d}/docker-compose.keycloak.yaml"
        if [ "$environment" = "prod" ]; then
            COMPOSE_FILES="$COMPOSE_FILES -f ${d}/docker-compose.keycloak-prod.yaml"
        fi
    fi

    if [ "${GIT_SERVER:-}" = "forgejo" ] || [ "${FORGEJO_DETECTED:-}" = "true" ]; then
        COMPOSE_FILES="$COMPOSE_FILES -f ${d}/docker-compose.forgejo.yaml"
        if [ "${KEYCLOAK_ENABLED:-}" = "true" ] || [ "${KEYCLOAK_DETECTED:-}" = "true" ]; then
            COMPOSE_FILES="$COMPOSE_FILES -f ${d}/docker-compose.forgejo-keycloak.yaml"
        fi
    fi

    if [ "${MATLAB_ENABLED:-}" = "true" ]; then
        COMPOSE_FILES="$COMPOSE_FILES -f ${d}/docker-compose.matlab.yaml"
    fi

    # Self-update sidecar: prod-only, opt-in. The file-exists guard keeps a
    # UPDATE_ENABLED=true .env working on a checkout that predates the overlay.
    if [ "$environment" = "prod" ] && [ "${UPDATE_ENABLED:-}" = "true" ] \
        && [ -f "${d}/docker-compose.updater.yaml" ]; then
        COMPOSE_FILES="$COMPOSE_FILES -f ${d}/docker-compose.updater.yaml"
        # The overlay interpolates these; every consumer (up/down/maintenance/
        # update, host or runner container) must agree on the same values.
        export COMPUTOR_REPO_DIR="${COMPUTOR_REPO_DIR:-$REPO_ROOT}"
        export HOST_UID="${HOST_UID:-$(id -u)}"
        export HOST_GID="${HOST_GID:-$(id -g)}"
    fi

    export COMPOSE_FILES
}

print_stack_summary() {
    local environment="$1"
    if [ "$environment" = "prod" ]; then
        log "Frontend: ${YELLOW}docker (production build)${NC}"
    else
        log "Frontend: ${YELLOW}run locally with 'cd computor-web && npm run dev'${NC}"
    fi
    log "Coder: ${YELLOW}$([ "${CODER_ENABLED:-}" = "true" ] && echo enabled || echo disabled)${NC}"
    log "Keycloak: ${YELLOW}$([ "${KEYCLOAK_ENABLED:-}" = "true" ] && echo enabled || echo disabled)${NC}"
    log "Forgejo: ${YELLOW}$([ "${GIT_SERVER:-}" = "forgejo" ] && echo enabled || echo disabled)${NC}"
    log "MATLAB worker: ${YELLOW}$([ "${MATLAB_ENABLED:-}" = "true" ] && echo enabled || echo disabled)${NC}"
    log "Self-update: ${YELLOW}$([ "${UPDATE_ENABLED:-}" = "true" ] && echo enabled || echo disabled)${NC}"
}

# docker compose with the assembled overlay set. Requires assemble_compose_files
# to have run.
compose() {
    [ -n "${COMPOSE_FILES:-}" ] || die "compose(): COMPOSE_FILES not assembled"
    # shellcheck disable=SC2086
    docker compose $COMPOSE_FILES "$@"
}

# Detect the running configuration from container names (used by `down` and
# `status` when no environment argument is given). Sets ENVIRONMENT and
# CODER_DETECTED / KEYCLOAK_DETECTED / FORGEJO_DETECTED. Returns 1 when no
# computor stack is running.
detect_environment() {
    docker ps --format "{{.Names}}" | grep -q "computor" || return 1
    docker ps --format "{{.Names}}" | grep -q "computor-minio" || return 1

    if docker ps --format "{{.Names}}" | grep -q "temporal-ui"; then
        ENVIRONMENT="dev"
    elif docker ps --format "{{.Names}}" | grep -q "uvicorn\|frontend"; then
        ENVIRONMENT="prod"
    else
        ENVIRONMENT="dev"
    fi

    docker ps --format "{{.Names}}" | grep -q "computor-coder"    && CODER_DETECTED=true
    docker ps --format "{{.Names}}" | grep -q "computor-keycloak" && KEYCLOAK_DETECTED=true
    docker ps --format "{{.Names}}" | grep -q "computor-forgejo"  && FORGEJO_DETECTED=true
    return 0
}

# redis-cli inside the stack's redis container (works from host and from the
# updater container — both talk to the same docker daemon).
redis_cli() {
    compose exec -T redis redis-cli -a "$REDIS_PASSWORD" "$@" 2>/dev/null
}

# Export GIT_COMMIT / GIT_BRANCH of the checked-out tree for image builds.
git_build_meta() {
    GIT_COMMIT="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
    GIT_BRANCH="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
    export GIT_COMMIT GIT_BRANCH
}

# ---------------------------------------------------------------------------
# Full-maintenance primitives (Redis flag + Traefik static-page catch-all +
# selective service stop). Moved verbatim from maintenance.sh.
# ---------------------------------------------------------------------------

# Services that keep running during full maintenance. The update executor
# overrides this to also keep the updater sidecar alive.
MAINTENANCE_KEEP_SERVICES="${MAINTENANCE_KEEP_SERVICES:-traefik static-server redis}"

maintenance_paths() {
    TRAEFIK_DYNAMIC_DIR="${SYSTEM_DEPLOYMENT_PATH}/traefik/dynamic"
    MAINTENANCE_CONFIG="${TRAEFIK_DYNAMIC_DIR}/maintenance.yaml"
    MAINTENANCE_PAGE_DIR="${SYSTEM_DEPLOYMENT_PATH}/shared/documents/_maintenance"
}

ensure_maintenance_page() {
    maintenance_paths
    mkdir -p "$MAINTENANCE_PAGE_DIR"
    if [ ! -f "$MAINTENANCE_PAGE_DIR/index.html" ]; then
        cp "${OPS_DIR}/maintenance/maintenance.html" "$MAINTENANCE_PAGE_DIR/index.html" \
            && log "  ${GREEN}Created maintenance page${NC}" \
            || warn "  Could not stage maintenance page (missing ${OPS_DIR}/maintenance/maintenance.html)"
    fi
}

activate_traefik_maintenance() {
    maintenance_paths
    mkdir -p "$TRAEFIK_DYNAMIC_DIR"
    cat > "$MAINTENANCE_CONFIG" << 'YAMLEOF'
http:
  routers:
    maintenance-catchall:
      rule: "PathPrefix(`/`)"
      entrypoints:
        - web
      priority: 9999
      service: maintenance-page
      middlewares:
        - maintenance-rewrite

  middlewares:
    maintenance-rewrite:
      replacePath:
        path: "/_maintenance/index.html"

  services:
    maintenance-page:
      loadBalancer:
        servers:
          - url: "http://static-server:8080"
YAMLEOF
    log "  ${GREEN}Traefik maintenance route activated${NC}"
}

deactivate_traefik_maintenance() {
    maintenance_paths
    if [ -f "$MAINTENANCE_CONFIG" ]; then
        rm -f "$MAINTENANCE_CONFIG"
        log "  ${GREEN}Traefik maintenance route removed${NC}"
    fi
}

set_redis_maintenance() {
    local active="$1"
    local message="$2"

    if [ "$active" = "1" ]; then
        redis_cli HSET "maintenance:state" \
            active "1" \
            message "$message" \
            activated_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
            activated_by "maintenance_script"
        log "  ${GREEN}Redis maintenance state: ACTIVE${NC}"
    else
        redis_cli DEL "maintenance:state" "maintenance:schedule"
        log "  ${GREEN}Redis maintenance state: CLEARED${NC}"
    fi
}

get_stoppable_services() {
    compose config --services 2>/dev/null | while read -r service; do
        local keep=false
        for keep_svc in $MAINTENANCE_KEEP_SERVICES; do
            if [ "$service" = "$keep_svc" ]; then
                keep=true
                break
            fi
        done
        [ "$keep" = false ] && echo "$service"
    done
}
