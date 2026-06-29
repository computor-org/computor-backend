#!/bin/bash

# Computor startup script
# Coder support is controlled via CODER_ENABLED in .env
# Usage:
#   ./startup.sh [dev|prod] [docker-compose-options]
#   ./startup.sh dev             # Development
#   ./startup.sh dev -d          # Development, detached
#   ./startup.sh prod -d         # Production, detached
#   ./startup.sh prod --build -d # Production, rebuild images

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="dev"
DOCKER_ARGS=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        dev|development)
            ENVIRONMENT="dev"
            shift
            ;;
        prod|production)
            ENVIRONMENT="prod"
            shift
            ;;
        *)
            # Collect remaining arguments for docker-compose
            DOCKER_ARGS="$DOCKER_ARGS $1"
            shift
            ;;
    esac
done

echo -e "${GREEN}=== Computor Startup Script ===${NC}"
echo -e "Environment: ${YELLOW}$ENVIRONMENT${NC}"

# Get script directory (should be project root)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
OPS_DIR="${SCRIPT_DIR}/ops"

# Check if environment files exist
check_env_file() {
    local file=$1
    local template="${OPS_DIR}/environments/$(basename $file).template"

    if [ ! -f "$file" ]; then
        if [ -f "$template" ]; then
            echo -e "${YELLOW}Warning: $file not found.${NC}"
            echo -e "Creating from template. Please edit $file with your configuration."
            cp "$template" "$file"
        else
            echo -e "${RED}Error: Neither $file nor $template found!${NC}"
            echo -e "Please run ./setup-env.sh first to create environment files."
            exit 1
        fi
    fi
}

# Check required environment files
if [ ! -f .env ]; then
    echo -e "${RED}No .env file found!${NC}"
    echo "Please create a .env file with your configuration."
    echo "You can copy from .env.common if it exists: cp .env.common .env"
    exit 1
fi

# Load environment file
echo -e "\n${GREEN}Loading environment file...${NC}"
set -a

# Load configuration from .env in root ONLY
source .env && echo "  ✓ .env"

set +a

# In production, PUBLIC_DOMAIN is the single source of truth for the public URLs.
# Derive the per-service public URLs from it here so the domain lives in exactly
# one place. Each uses ${VAR:-...}, so an explicitly-set value in .env still wins
# (per-service override). Dev is untouched: PUBLIC_DOMAIN is empty there and each
# service keeps its own localhost:port URL from .env. setup-env.sh leaves these
# four empty in a prod .env so PUBLIC_DOMAIN drives them.
if [ "$ENVIRONMENT" = "prod" ] && [ -n "${PUBLIC_DOMAIN:-}" ]; then
    PUBLIC_DOMAIN="${PUBLIC_DOMAIN%/}"            # tolerate a trailing slash
    _pd_host="${PUBLIC_DOMAIN#*://}"; _pd_host="${_pd_host%%/*}"  # strip scheme + path
    export NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-${PUBLIC_DOMAIN}/api}"
    export KEYCLOAK_PUBLIC_URL="${KEYCLOAK_PUBLIC_URL:-${PUBLIC_DOMAIN}/auth}"
    export FORGEJO_ROOT_URL="${FORGEJO_ROOT_URL:-${PUBLIC_DOMAIN}/forgejo}"
    export FORGEJO_DOMAIN="${FORGEJO_DOMAIN:-${_pd_host}}"
    echo -e "  ${GREEN}✓${NC} Derived public URLs from PUBLIC_DOMAIN=${PUBLIC_DOMAIN}"
fi

# Ensure the shared Forgejo<->Keycloak client secret exists and is persisted in .env.
# It must be stable (the realm import and the compose env have to agree on one value)
# and is only needed when both Keycloak and Forgejo are enabled. This self-heals .env
# files created before the secret existed, so upgrading never needs a manual edit.
if [ "$KEYCLOAK_ENABLED" = "true" ] && [ "$GIT_SERVER" = "forgejo" ] && [ -z "${FORGEJO_KEYCLOAK_CLIENT_SECRET:-}" ]; then
    FORGEJO_KEYCLOAK_CLIENT_SECRET=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p -c 256)
    sed -i.bak '/^FORGEJO_KEYCLOAK_CLIENT_SECRET=/d' .env && rm -f .env.bak
    printf 'FORGEJO_KEYCLOAK_CLIENT_SECRET=%s\n' "$FORGEJO_KEYCLOAK_CLIENT_SECRET" >> .env
    export FORGEJO_KEYCLOAK_CLIENT_SECRET
    echo -e "  ${GREEN}✓${NC} Generated and persisted FORGEJO_KEYCLOAK_CLIENT_SECRET to .env"
fi

# Build docker-compose command
COMPOSE_FILES="-f ops/docker/docker-compose.base.yaml -f ops/docker/docker-compose.$ENVIRONMENT.yaml"

# Include web frontend in production (in dev, run `next dev` locally)
if [ "$ENVIRONMENT" = "prod" ]; then
    COMPOSE_FILES="$COMPOSE_FILES -f ops/docker/docker-compose.web.yaml"
    echo -e "Frontend: ${YELLOW}docker (production build)${NC}"
else
    echo -e "Frontend: ${YELLOW}run locally with 'cd computor-web && npm run dev'${NC}"
fi

if [ "$CODER_ENABLED" = "true" ]; then
    echo -e "Coder: ${YELLOW}enabled${NC}"
    COMPOSE_FILES="$COMPOSE_FILES -f ops/docker/docker-compose.coder.yaml"
    export POSTGRES_MULTIPLE_DATABASES="computor,coder"
else
    echo -e "Coder: ${YELLOW}disabled${NC} (set CODER_ENABLED=true in .env to enable)"
    export POSTGRES_MULTIPLE_DATABASES="computor"
fi

if [ "$KEYCLOAK_ENABLED" = "true" ]; then
    echo -e "Keycloak: ${YELLOW}enabled${NC}"
    COMPOSE_FILES="$COMPOSE_FILES -f ops/docker/docker-compose.keycloak.yaml"
    if [ "$ENVIRONMENT" = "prod" ]; then
        COMPOSE_FILES="$COMPOSE_FILES -f ops/docker/docker-compose.keycloak-prod.yaml"
    fi
else
    echo -e "Keycloak: ${YELLOW}disabled${NC} (set KEYCLOAK_ENABLED=true in .env to enable)"
fi

if [ "$GIT_SERVER" = "forgejo" ]; then
    echo -e "Forgejo: ${YELLOW}enabled${NC}"
    COMPOSE_FILES="$COMPOSE_FILES -f ops/docker/docker-compose.forgejo.yaml"
else
    echo -e "Forgejo: ${YELLOW}disabled${NC} (set GIT_SERVER=forgejo in .env to enable)"
fi

if [ "$GIT_SERVER" = "forgejo" ] && [ "$KEYCLOAK_ENABLED" = "true" ]; then
    echo -e "Forgejo-Keycloak OIDC: ${YELLOW}auto-setup enabled${NC}"
    COMPOSE_FILES="$COMPOSE_FILES -f ops/docker/docker-compose.forgejo-keycloak.yaml"
fi

if [ "$MATLAB_ENABLED" = "true" ]; then
    echo -e "MATLAB worker: ${YELLOW}enabled${NC}"
    COMPOSE_FILES="$COMPOSE_FILES -f ops/docker/docker-compose.matlab.yaml"
else
    echo -e "MATLAB worker: ${YELLOW}disabled${NC} (set MATLAB_ENABLED=true in .env to enable)"
fi

# Function to safely create directories
create_dir_if_needed() {
    local dir_path="$1"
    if [ ! -d "$dir_path" ]; then
        echo "  Creating: $dir_path"
        mkdir -p "$dir_path"
    fi
}

# Pre-create directories
echo -e "\n${GREEN}Creating necessary directories...${NC}"

# Database directories
create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/postgres"
create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/temporal-postgres"
create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/redis"
create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/redis-data"

# MinIO storage
create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/minio/data"

# Shared application directories
create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/shared"
for dir in documents courses course-contents defaults repositories; do
    create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/shared/$dir"
done

# Traefik dynamic config directory
create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/traefik/dynamic"

# Clear stale maintenance mode config (if services are starting, maintenance is over)
if [ -f "${SYSTEM_DEPLOYMENT_PATH}/traefik/dynamic/maintenance.yaml" ]; then
    echo -e "  ${YELLOW}Clearing stale maintenance mode config${NC}"
    rm -f "${SYSTEM_DEPLOYMENT_PATH}/traefik/dynamic/maintenance.yaml"
fi

# Coder directories (if enabled)
if [ "$CODER_ENABLED" = "true" ]; then
    create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/coder"
    create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/coder/home"
    # Coder container runs as UID 1000 — ensure it can write to its home directory
    chmod 777 "${SYSTEM_DEPLOYMENT_PATH}/coder/home" 2>/dev/null || true
    create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/coder/registry"
    create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/coder/templates"

    # Seed default templates from repo (only copies missing ones, never overwrites)
    if [ -d "${SCRIPT_DIR}/computor-coder/deployment/templates" ]; then
        echo -e "  ${GREEN}Seeding Coder templates...${NC}"
        for tpl_dir in "${SCRIPT_DIR}/computor-coder/deployment/templates"/*/; do
            tpl_name=$(basename "$tpl_dir")
            if [ ! -d "${SYSTEM_DEPLOYMENT_PATH}/coder/templates/${tpl_name}" ]; then
                echo "    Copying template: ${tpl_name}"
                cp -r "$tpl_dir" "${SYSTEM_DEPLOYMENT_PATH}/coder/templates/${tpl_name}"
            else
                echo "    Template already exists: ${tpl_name} (skipping)"
            fi
        done
    fi

    # Verify the Coder container will be able to reach the Docker socket.
    # Coder's provisioner runs as a non-root user (uid 1000) and creates the
    # workspace's docker volume/image/container through the mounted socket, so
    # it must belong to the group that owns the socket *inside a container*.
    echo -e "\n${GREEN}Checking Docker socket access for Coder...${NC}"

    # Daemon reachable at all?
    if ! docker info >/dev/null 2>&1; then
        echo -e "${RED}ERROR: Docker daemon is not reachable.${NC}"
        echo "  Start Docker/OrbStack and re-run, or set CODER_ENABLED=false in .env."
        exit 1
    fi

    # The socket's group as seen INSIDE a container — the value group_add needs.
    # Host-side stat is wrong on Docker Desktop / OrbStack, where the in-container
    # socket is root:root (gid 0); probe a throwaway container for the truth.
    SOCK_GID=$(docker run --rm -v /var/run/docker.sock:/var/run/docker.sock alpine \
        stat -c '%g' /var/run/docker.sock 2>/dev/null)

    if [ -z "$DOCKER_GID" ]; then
        if [ -n "$SOCK_GID" ]; then
            DOCKER_GID="$SOCK_GID"
            echo "  Detected DOCKER_GID=$DOCKER_GID"
        else
            echo -e "${RED}ERROR: Could not detect the Docker socket group.${NC}"
            echo "  Set DOCKER_GID in .env to the gid of /var/run/docker.sock inside a container."
            exit 1
        fi
    else
        echo "  Using DOCKER_GID=$DOCKER_GID (from .env)"
        if [ -n "$SOCK_GID" ] && [ "$DOCKER_GID" != "$SOCK_GID" ]; then
            echo -e "  ${YELLOW}Note: socket gid inside a container is $SOCK_GID but DOCKER_GID=$DOCKER_GID.${NC}"
        fi
    fi
    export DOCKER_GID

    # End-to-end: a non-root container joined to DOCKER_GID must be able to write
    # (i.e. connect) to the socket — exactly what Coder's terraform does. This
    # catches a wrong gid before the first workspace build fails with
    # "permission denied while trying to connect to the Docker daemon socket".
    if ! docker run --rm --user 1000:1000 --group-add "$DOCKER_GID" \
            -v /var/run/docker.sock:/var/run/docker.sock alpine \
            test -w /var/run/docker.sock >/dev/null 2>&1; then
        echo -e "${RED}ERROR: a non-root container in group $DOCKER_GID still cannot access /var/run/docker.sock.${NC}"
        echo "  Coder workspace provisioning would fail with 'permission denied'."
        echo "  Set DOCKER_GID=${SOCK_GID:-<gid of docker.sock inside a container>} in .env and re-run."
        exit 1
    fi
    echo -e "  ${GREEN}OK — non-root container can reach the Docker socket (gid $DOCKER_GID).${NC}"
fi

# Copy defaults if source exists
if [ -d "computor-backend/src/defaults" ]; then
    echo -e "\n${GREEN}Copying default files...${NC}"
    cp -r computor-backend/src/defaults/* "${SYSTEM_DEPLOYMENT_PATH}/shared/defaults/" 2>/dev/null || true
fi

# Optional: Create Forgejo directories if enabled
if [ "$GIT_SERVER" = "forgejo" ]; then
    create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/forgejo/postgres"
    create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/forgejo/data"
fi

# Optional: Create Keycloak directories if enabled
if [ "${KEYCLOAK_ENABLED}" = "true" ]; then
    echo -e "\n${GREEN}Setting up Keycloak directories...${NC}"
    create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/keycloak-db"
    create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/keycloak/imports"
    create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/keycloak/themes"

    # Copy realm config, substituting the client secrets from .env. Both placeholders
    # are hex (no '/'), so the /-delimited sed is safe. PLACEHOLDER_CLIENT_SECRET is not
    # a substring of PLACEHOLDER_FORGEJO_CLIENT_SECRET, so the two never collide.
    if [ -f "data/keycloak/computor-realm.json" ]; then
        echo "  Writing Keycloak realm configuration (substituting client secrets)..."
        sed -e "s/PLACEHOLDER_CLIENT_SECRET/${KEYCLOAK_CLIENT_SECRET}/g" \
            -e "s/PLACEHOLDER_FORGEJO_CLIENT_SECRET/${FORGEJO_KEYCLOAK_CLIENT_SECRET}/g" \
            data/keycloak/computor-realm.json \
            > "${SYSTEM_DEPLOYMENT_PATH}/keycloak/imports/computor-realm.json"
    fi

    # Sync custom login theme(s) into the mounted themes directory
    if [ -d "data/keycloak/themes" ]; then
        echo "  Syncing Keycloak themes..."
        cp -r data/keycloak/themes/. "${SYSTEM_DEPLOYMENT_PATH}/keycloak/themes/"
    fi

    # Brokered external identity providers (optional). The real provider list is
    # local-only (gitignored), like .env: seed it from the committed example on
    # first run, then stage it to the deploy path where the keycloak-idp-setup
    # one-shot reads it. Secrets are NOT in this file — they stay in .env.
    create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/keycloak/idp"
    if [ ! -f "data/keycloak/identity-providers.json" ] && [ -f "data/keycloak/identity-providers.example.json" ]; then
        echo "  Seeding data/keycloak/identity-providers.json from example (edit it to add providers)..."
        cp "data/keycloak/identity-providers.example.json" "data/keycloak/identity-providers.json"
    fi
    if [ -f "data/keycloak/identity-providers.json" ]; then
        cp "data/keycloak/identity-providers.json" "${SYSTEM_DEPLOYMENT_PATH}/keycloak/idp/identity-providers.json"
    fi
fi

# Make postgres init script executable. Tolerate a deploy user who is not the
# file owner (the file ships executable from git, so this is only a touch-up).
if [ -f "docker/postgres-init/01-create-multiple-databases.sh" ]; then
    chmod +x docker/postgres-init/01-create-multiple-databases.sh 2>/dev/null || true
fi

# The Python service images (api + temporal workers) inherit from a shared base
# image (docker/base/Dockerfile); the matlab worker COPYs from it. Build it first
# so their `FROM computor-base:latest` resolves. Rebuild when --build is requested
# or when the image is missing (cached/fast otherwise).
if [[ "$DOCKER_ARGS" == *"--build"* ]] || ! docker image inspect computor-base:latest >/dev/null 2>&1; then
    echo -e "\n${GREEN}Building shared base image (computor-base)...${NC}"
    docker build -f docker/base/Dockerfile -t computor-base:latest .
fi

# Start services
echo -e "\n${GREEN}Starting Computor services...${NC}"
echo "Command: docker compose $COMPOSE_FILES up $DOCKER_ARGS"

docker compose $COMPOSE_FILES up $DOCKER_ARGS

# Show status if running in detached mode
if [[ "$DOCKER_ARGS" == *"-d"* ]]; then
    echo -e "\n${GREEN}Services status:${NC}"
    docker compose $COMPOSE_FILES ps

    echo -e "\n${GREEN}Service URLs:${NC}"
    echo "  • API: http://localhost:${API_PORT:-8000}"
    echo "  • Traefik: http://localhost:${TRAEFIK_HTTP_PORT:-8080}"

    if [ "$ENVIRONMENT" = "prod" ]; then
        echo "  • Frontend: http://localhost:${TRAEFIK_HTTP_PORT:-8080}"
    fi

    if [ "$ENVIRONMENT" = "dev" ]; then
        echo "  • Temporal UI: http://localhost:${TEMPORAL_UI_PORT:-8088}"
        echo "  • MinIO Console: http://localhost:${MINIO_CONSOLE_PORT:-9001}"
    fi

    if [ "$CODER_ENABLED" = "true" ]; then
        # Coder's server is internal-only (bound to 127.0.0.1, not behind Traefik);
        # only workspaces are exposed, via Traefik.
        echo "  • Coder API (local access only): http://localhost:7080"
        echo "  • Coder workspaces: ${CODER_WORKSPACE_BASE_URL:-http://localhost:${TRAEFIK_HTTP_PORT:-8080}/coder}"
    fi

    if [ "$GIT_SERVER" = "forgejo" ]; then
        echo "  • Forgejo: http://localhost:${FORGEJO_PORT:-3030}"
    fi

    echo -e "\n${GREEN}To stop services:${NC}"
    # Use stop.sh, not raw `docker compose down`: in prod the public URLs are derived
    # from PUBLIC_DOMAIN and left empty in .env, so a bare compose command fails on
    # ${NEXT_PUBLIC_API_URL:?}. stop.sh re-derives them.
    echo "  ./stop.sh $ENVIRONMENT"

    echo -e "\n${GREEN}To view logs:${NC}"
    echo "  docker compose $COMPOSE_FILES logs -f [service-name]"
fi