#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${RED}=== COMPLETE CODER WIPE SCRIPT ===${NC}"
echo -e "${YELLOW}WARNING: This will COMPLETELY delete all Coder data including database!${NC}"
echo ""
read -p "Are you sure you want to wipe ALL Coder data? Type 'yes' to confirm: " confirmation

if [ "$confirmation" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

# Source environment for credentials
source .env

echo -e "\n${YELLOW}1. Stopping all Coder containers...${NC}"
docker stop computor-coder computor-coder-registry 2>/dev/null
docker rm -f computor-coder computor-coder-registry 2>/dev/null
docker rm -f docker-coder-admin-setup-1 2>/dev/null
echo "  ✓ Containers stopped and removed"

echo -e "\n${YELLOW}2. Removing Coder Docker volumes...${NC}"
docker volume rm -f computor-coder-home computor-coder-registry 2>/dev/null
echo "  ✓ Volumes removed"

echo -e "\n${YELLOW}3. Wiping Coder database (separate from main DB)...${NC}"
# Check if Coder's dedicated postgres is running
if docker ps | grep -q computor-coder-postgres; then
    # Stop Coder postgres to ensure clean wipe
    docker stop computor-coder-postgres 2>/dev/null
    docker rm -f computor-coder-postgres 2>/dev/null
    echo "  ✓ Coder database container stopped and removed"

    # Remove Coder database directory (bind mount)
    if [ -n "$SYSTEM_DEPLOYMENT_PATH" ] && [ -d "$SYSTEM_DEPLOYMENT_PATH/coder-postgres" ]; then
        sudo rm -rf "$SYSTEM_DEPLOYMENT_PATH/coder-postgres"
        echo "  ✓ Coder database files removed from $SYSTEM_DEPLOYMENT_PATH/coder-postgres"
    fi
else
    echo "  ✓ Coder database not running (will be recreated on next startup)"
fi

echo -e "\n${YELLOW}4. Removing Coder workspace images...${NC}"
docker images | grep "localhost:5000/computor-workspace" | awk '{print $3}' | xargs -r docker rmi -f 2>/dev/null
docker images | grep "coder" | grep "workspace" | awk '{print $3}' | xargs -r docker rmi -f 2>/dev/null
echo "  ✓ Images removed"

echo -e "\n${YELLOW}5. Clearing Coder registry data...${NC}"
# The registry uses Docker volume (already removed in step 2)
# Just clean up any dangling Docker resources
docker system prune -f 2>/dev/null
echo "  ✓ Registry data cleared"

echo -e "\n${GREEN}✓ COMPLETE Coder wipe finished!${NC}"
echo ""
echo "Next steps:"
echo "1. Ensure CODER_ENABLED=true in .env, then: bash startup.sh dev -d"
echo "2. Coder will be completely fresh - new database, new admin user"
echo "3. Build images and push templates via admin API:"
echo "   POST /coder/admin/images/build"
echo "   POST /coder/admin/templates/push"
echo "4. Admin will be created with credentials from .env:"
echo "   - Email: $CODER_ADMIN_EMAIL"
echo "   - Password: $CODER_ADMIN_PASSWORD"
echo ""
echo "NOTE: Make sure .env has the credentials you want BEFORE restarting!"