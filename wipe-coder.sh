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

echo -e "\n${YELLOW}Stopping all containers...${NC}"
docker stop computor-coder computor-coder-registry 2>/dev/null
docker rm computor-coder computor-coder-registry 2>/dev/null
docker rm docker-coder-admin-setup-1 docker-coder-template-setup-1 2>/dev/null
docker rm docker-coder-image-builder-python-1 docker-coder-image-builder-matlab-1 2>/dev/null

echo -e "\n${YELLOW}Removing Coder Docker volumes...${NC}"
docker volume rm computor-coder-home computor-coder-registry 2>/dev/null

echo -e "\n${YELLOW}Cleaning Coder database (if PostgreSQL is running)...${NC}"
# Check if postgres is running
if docker ps | grep -q postgres; then
    # Source environment to get DB credentials
    source .env

    # Drop the Coder database and recreate it empty
    docker exec docker-postgres-1 psql -U $POSTGRES_USER -d $POSTGRES_DB -c "DROP DATABASE IF EXISTS coder;" 2>/dev/null
    docker exec docker-postgres-1 psql -U $POSTGRES_USER -d $POSTGRES_DB -c "CREATE DATABASE coder;" 2>/dev/null
    echo "  ✓ Coder database wiped"
else
    echo "  ⚠ PostgreSQL not running - skipping database cleanup"
    echo "  To clean database later, run:"
    echo "    docker exec docker-postgres-1 psql -U \$POSTGRES_USER -c 'DROP DATABASE IF EXISTS coder;'"
fi

echo -e "\n${YELLOW}Removing any Coder workspace images...${NC}"
docker images | grep "localhost:5000/computor-workspace" | awk '{print $3}' | xargs -r docker rmi -f 2>/dev/null

echo -e "\n${GREEN}✓ Coder data wipe complete!${NC}"
echo ""
echo "To reinitialize Coder:"
echo "  1. Start services: bash startup.sh dev --coder"
echo "  2. Coder will recreate its database and admin user automatically"
echo ""
echo "Note: User workspace data in Docker volumes has been deleted."
echo "      Templates in computor-coder/deployment/templates/ are preserved."