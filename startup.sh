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

# Build docker-compose command
COMPOSE_FILES="-f ops/docker/docker-compose.base.yaml -f ops/docker/docker-compose.$ENVIRONMENT.yaml"
if [ "$CODER_ENABLED" = "true" ]; then
    echo -e "Coder: ${YELLOW}enabled${NC}"
    COMPOSE_FILES="$COMPOSE_FILES -f ops/docker/docker-compose.coder.yaml"
    export POSTGRES_MULTIPLE_DATABASES="computor,coder"
else
    echo -e "Coder: ${YELLOW}disabled${NC} (set CODER_ENABLED=true in .env to enable)"
    export POSTGRES_MULTIPLE_DATABASES="computor"
fi

# Function to safely create directories
create_dir_if_needed() {
    local dir_path="$1"
    if [ ! -d "$dir_path" ]; then
        echo "  Creating: $dir_path"
        mkdir -p "$dir_path"
    elif [ ! -w "$dir_path" ]; then
        echo -e "${RED}ERROR: Directory $dir_path exists but is not writable!${NC}"
        echo "  Owner: $(stat -c '%U:%G' "$dir_path" 2>/dev/null || stat -f '%Su:%Sg' "$dir_path" 2>/dev/null)"
        echo "  Please run: sudo chown -R $(whoami):$(whoami) ${SYSTEM_DEPLOYMENT_PATH}"
        echo "  Or remove it: sudo rm -rf ${SYSTEM_DEPLOYMENT_PATH}"
        exit 1
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

# Coder directories (if enabled)
if [ "$CODER_ENABLED" = "true" ]; then
    create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/coder"
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

    # Auto-detect DOCKER_GID if not set (required for Coder to access Docker socket)
    if [ -z "$DOCKER_GID" ]; then
        echo -e "\n${GREEN}Auto-detecting Docker group ID...${NC}"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS: get GID of docker.sock
            DOCKER_GID=$(stat -f '%g' /var/run/docker.sock 2>/dev/null || echo "")
        else
            # Linux: get docker group ID
            DOCKER_GID=$(getent group docker | cut -d: -f3 2>/dev/null || stat -c '%g' /var/run/docker.sock 2>/dev/null || echo "")
        fi

        if [ -n "$DOCKER_GID" ]; then
            export DOCKER_GID
            echo "  DOCKER_GID=$DOCKER_GID"
        else
            echo -e "${RED}ERROR: Could not detect Docker group ID${NC}"
            echo "  Please set DOCKER_GID manually in your .env file"
            echo "  You can find it with: getent group docker | cut -d: -f3"
            exit 1
        fi
    fi
fi

# Copy defaults if source exists
if [ -d "computor-backend/src/defaults" ]; then
    echo -e "\n${GREEN}Copying default files...${NC}"
    cp -r computor-backend/src/defaults/* "${SYSTEM_DEPLOYMENT_PATH}/shared/defaults/" 2>/dev/null || true
fi

# Optional: Create Keycloak directories if enabled
if [ "${KEYCLOAK_ENABLED}" = "true" ]; then
    echo -e "\n${GREEN}Setting up Keycloak directories...${NC}"
    create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/keycloak/imports"
    create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/keycloak/themes"

    # Copy Keycloak realm configuration if it exists
    if [ -f "data/keycloak/computor-realm.json" ]; then
        echo "  Copying Keycloak realm configuration..."
        cp data/keycloak/computor-realm.json "${SYSTEM_DEPLOYMENT_PATH}/keycloak/imports/"
    fi
fi

# Make postgres init script executable
if [ -f "docker/postgres-init/01-create-multiple-databases.sh" ]; then
    chmod +x docker/postgres-init/01-create-multiple-databases.sh
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

    if [ "$ENVIRONMENT" = "dev" ]; then
        echo "  • Temporal UI: http://localhost:${TEMPORAL_UI_PORT:-8088}"
        echo "  • MinIO Console: http://localhost:${MINIO_CONSOLE_PORT:-9001}"
    fi

    if [ "$CODER_ENABLED" = "true" ]; then
        echo "  • Coder: ${CODER_PROTOCOL:-https}://${CODER_DOMAIN}:${CODER_EXTERNAL_PORT:-8446}"
    fi

    echo -e "\n${GREEN}To stop services:${NC}"
    echo "  docker compose $COMPOSE_FILES down"

    echo -e "\n${GREEN}To view logs:${NC}"
    echo "  docker compose $COMPOSE_FILES logs -f [service-name]"
fi