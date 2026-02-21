#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${RED}=== CODER DATA WIPE SCRIPT ===${NC}"
echo -e "${YELLOW}WARNING: This will permanently delete all Coder data!${NC}"
echo ""
read -p "Are you sure you want to wipe all Coder data? Type 'yes' to confirm: " confirmation

if [ "$confirmation" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

# Source environment for paths
source .env

# Detect which environment is running (dev or prod) for compose file selection
ENVIRONMENT=""
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "temporal-ui"; then
    ENVIRONMENT="dev"
elif docker ps --format '{{.Names}}' 2>/dev/null | grep -q "uvicorn"; then
    ENVIRONMENT="prod"
else
    ENVIRONMENT="dev"
fi

COMPOSE_FILES="-f ops/docker/docker-compose.base.yaml -f ops/docker/docker-compose.$ENVIRONMENT.yaml -f ops/docker/docker-compose.coder.yaml"

echo -e "\n${YELLOW}Stopping all Coder services via docker compose...${NC}"
docker compose $COMPOSE_FILES stop coder-postgres coder coder-registry temporal-worker-coder 2>/dev/null
docker compose $COMPOSE_FILES rm -f coder-postgres coder coder-registry temporal-worker-coder 2>/dev/null

echo -e "\n${YELLOW}Removing Coder Docker volumes...${NC}"
docker volume rm -f computor-coder-home computor-coder-registry 2>/dev/null

echo -e "\n${YELLOW}Removing Coder database (separate from main DB)...${NC}"
# Remove Coder database files (bind mount) — always attempt, not just when container is running
if [ -n "$SYSTEM_DEPLOYMENT_PATH" ] && [ -d "$SYSTEM_DEPLOYMENT_PATH/coder-postgres" ]; then
    sudo rm -rf "$SYSTEM_DEPLOYMENT_PATH/coder-postgres"
    echo "  Coder database files removed"
else
    echo "  No Coder database files to remove"
fi

echo -e "\n${YELLOW}Removing any Coder workspace images...${NC}"
docker images | grep "localhost:5000/computor-workspace" | awk '{print $3}' | xargs -r docker rmi -f 2>/dev/null

echo -e "\n${GREEN}=== Coder data wipe complete! ===${NC}"
echo ""
echo "To reinitialize Coder:"
echo "  1. Ensure CODER_ENABLED=true in .env"
echo "  2. Start services: bash startup.sh dev -d"
echo "  3. Coder will recreate its database and admin user automatically"
echo "  4. Build images and push templates via admin API:"
echo "     POST /coder/admin/images/build"
echo "     POST /coder/admin/templates/push"
echo ""
echo "Note: User workspace data in Docker volumes has been deleted."
echo "      Templates in \${SYSTEM_DEPLOYMENT_PATH}/coder/templates/ are preserved."
