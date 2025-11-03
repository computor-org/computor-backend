#!/bin/bash

# Stop on error
set -e

# Export env vars from .env
set -a
source .env
set +a

ENVIRONMENT=${1:-dev}

# Shift the first argument if it's an environment (dev/prod)
if [[ "$1" == "dev" ]] || [[ "$1" == "prod" ]]; then
    shift
fi

# Capture any additional docker-compose arguments (like --build)
DOCKER_ARGS="$@"

DOCKERCFILE="docker-compose-${ENVIRONMENT}.yaml"

# Function to safely create directories
create_dir_if_needed() {
    local dir_path="$1"
    if [ ! -d "$dir_path" ]; then
        echo "Creating directory: $dir_path"
        mkdir -p "$dir_path"
    elif [ ! -w "$dir_path" ]; then
        echo "ERROR: Directory $dir_path exists but is not writable!"
        echo "  Owner: $(stat -c '%U:%G' "$dir_path" 2>/dev/null)"
        echo "  Please run: sudo chown -R $(whoami):$(whoami) ${SYSTEM_DEPLOYMENT_PATH}"
        echo "  Or remove it: sudo rm -rf ${SYSTEM_DEPLOYMENT_PATH}"
        exit 1
    fi
}

# Pre-create ALL Docker volume mount points with correct ownership
# This prevents Docker from creating them as root
echo "=== Pre-creating Docker volume directories ==="

# # Database directories
# create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/postgres"
# create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/temporal-postgres"
# create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/redis"
# create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/redis-data"

# # MinIO storage
# create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/minio/data"

# CRITICAL: Create shared directory BEFORE Docker mounts it
create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/shared"

# Now create the application subdirectories
destination="${SYSTEM_DEPLOYMENT_PATH}/shared"

directories=(
    "documents"
    "courses"
    "course-contents"
    "defaults"
    "repositories"
)

echo "=== Creating application directories ==="
for dir in "${directories[@]}"; do
    full_path="${destination}/${dir}"
    create_dir_if_needed "$full_path"
done

# Copy defaults if source exists
if [ -d "computor-backend/src/defaults" ]; then
    echo "Copying defaults..."
    cp -r computor-backend/src/defaults "${SYSTEM_DEPLOYMENT_PATH}/shared"
fi

# Create Keycloak directories if they don't exist
keycloak_imports="${SYSTEM_DEPLOYMENT_PATH}/keycloak/imports"
keycloak_themes="${SYSTEM_DEPLOYMENT_PATH}/keycloak/themes"

create_dir_if_needed "$keycloak_imports"
create_dir_if_needed "$keycloak_themes"

# Copy Keycloak realm configuration if it exists
if [ -f "data/keycloak/computor-realm.json" ]; then
    echo "Copying Keycloak realm configuration..."
    cp data/keycloak/computor-realm.json "$keycloak_imports/"
fi

echo "=== Starting Computor Server ==="
echo "Environment: $ENVIRONMENT"
echo "Docker compose file: $DOCKERCFILE"

docker-compose -f $DOCKERCFILE up $DOCKER_ARGS