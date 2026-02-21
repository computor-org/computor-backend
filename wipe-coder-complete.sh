#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse flags
WIPE_TEMPLATES=false
for arg in "$@"; do
    case "$arg" in
        --templates) WIPE_TEMPLATES=true ;;
    esac
done

echo -e "${RED}=== COMPLETE CODER WIPE SCRIPT ===${NC}"
echo -e "${YELLOW}WARNING: This will COMPLETELY delete all Coder data including database!${NC}"
if [ "$WIPE_TEMPLATES" = true ]; then
    echo -e "${YELLOW}         --templates flag set: will also remove deployed templates${NC}"
fi
echo ""
read -p "Are you sure you want to wipe ALL Coder data? Type 'yes' to confirm: " confirmation

if [ "$confirmation" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

# Source environment for credentials and paths
source .env

# Detect which environment is running (dev or prod) for compose file selection
ENVIRONMENT=""
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "temporal-ui"; then
    ENVIRONMENT="dev"
elif docker ps --format '{{.Names}}' 2>/dev/null | grep -q "uvicorn"; then
    ENVIRONMENT="prod"
else
    # Default to dev if we can't detect
    ENVIRONMENT="dev"
fi

COMPOSE_FILES="-f ops/docker/docker-compose.base.yaml -f ops/docker/docker-compose.$ENVIRONMENT.yaml -f ops/docker/docker-compose.coder.yaml"

echo -e "\n${YELLOW}1. Stopping all Coder services via docker compose...${NC}"
# Use docker compose to properly stop and remove all coder-related containers
# This handles all services including temporal-worker-coder (which has no explicit container_name)
docker compose $COMPOSE_FILES stop coder-postgres coder coder-registry temporal-worker-coder 2>/dev/null
docker compose $COMPOSE_FILES rm -f coder-postgres coder coder-registry temporal-worker-coder 2>/dev/null
echo "  Coder containers stopped and removed"

echo -e "\n${YELLOW}2. Removing Coder Docker volumes...${NC}"
docker volume rm -f computor-coder-home computor-coder-registry 2>/dev/null
echo "  Volumes removed"

echo -e "\n${YELLOW}3. Wiping Coder database (separate from main DB)...${NC}"
# Remove Coder database directory (bind mount) — always attempt, not just when container is running
if [ -n "$SYSTEM_DEPLOYMENT_PATH" ] && [ -d "$SYSTEM_DEPLOYMENT_PATH/coder-postgres" ]; then
    sudo rm -rf "$SYSTEM_DEPLOYMENT_PATH/coder-postgres"
    echo "  Coder database files removed from $SYSTEM_DEPLOYMENT_PATH/coder-postgres"
else
    echo "  No Coder database files to remove"
fi

echo -e "\n${YELLOW}4. Removing Coder workspace images...${NC}"
docker images | grep "localhost:5000/computor-workspace" | awk '{print $3}' | xargs -r docker rmi -f 2>/dev/null
docker images | grep "coder" | grep "workspace" | awk '{print $3}' | xargs -r docker rmi -f 2>/dev/null
echo "  Images removed"

if [ "$WIPE_TEMPLATES" = true ]; then
    echo -e "\n${YELLOW}5. Removing Coder templates...${NC}"
    # Templates are re-seeded from the repo on next startup.sh
    if [ -n "$SYSTEM_DEPLOYMENT_PATH" ] && [ -d "$SYSTEM_DEPLOYMENT_PATH/coder" ]; then
        sudo rm -rf "$SYSTEM_DEPLOYMENT_PATH/coder"
        echo "  Coder directory removed from $SYSTEM_DEPLOYMENT_PATH/coder"
    else
        echo "  No Coder directory to remove"
    fi
else
    echo -e "\n${YELLOW}5. Skipping Coder templates (use --templates to also remove)${NC}"
fi

echo -e "\n${YELLOW}6. Clearing Coder registry data...${NC}"
# The registry uses Docker volume (already removed in step 2)
# Just clean up any dangling Docker resources
docker system prune -f 2>/dev/null
echo "  Registry data cleared"

echo -e "\n${GREEN}=== COMPLETE Coder wipe finished! ===${NC}"
echo ""
echo "Next steps:"
echo "1. Ensure CODER_ENABLED=true in .env, then: bash startup.sh dev -d"
echo "2. Coder will be completely fresh - new database, new admin user"
echo "3. Build images and push templates via admin API:"
echo "   POST /coder/admin/images/build"
echo "   POST /coder/admin/templates/push"
echo "4. Admin will be created automatically from .env credentials:"
echo "   - Email: $CODER_ADMIN_EMAIL"
echo "   - Password: $CODER_ADMIN_PASSWORD"
echo ""
echo "NOTE: Make sure .env has the credentials you want BEFORE restarting!"
