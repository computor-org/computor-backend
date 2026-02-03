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
docker rm -f docker-coder-admin-setup-1 docker-coder-template-setup-1 2>/dev/null
docker rm -f docker-coder-image-builder-python-1 docker-coder-image-builder-matlab-1 2>/dev/null
echo "  ✓ Containers stopped and removed"

echo -e "\n${YELLOW}2. Removing Coder Docker volumes...${NC}"
docker volume rm -f computor-coder-home computor-coder-registry 2>/dev/null
echo "  ✓ Volumes removed"

echo -e "\n${YELLOW}3. Dropping and recreating Coder database...${NC}"
# Check if postgres is running
if docker ps | grep -q docker-postgres-1; then
    # Drop ALL tables and data in Coder database
    docker exec docker-postgres-1 psql -U $POSTGRES_USER -c "DROP DATABASE IF EXISTS coder WITH (FORCE);" 2>/dev/null
    echo "  ✓ Coder database dropped"

    # Recreate empty database
    docker exec docker-postgres-1 psql -U $POSTGRES_USER -c "CREATE DATABASE coder;" 2>/dev/null
    echo "  ✓ Empty Coder database created"

    # Also clear any Coder data in main database (if any)
    docker exec docker-postgres-1 psql -U $POSTGRES_USER -d $POSTGRES_DB -c "DELETE FROM \"user\" WHERE email LIKE '%@computor.edu' AND username = 'admin';" 2>/dev/null
else
    echo "  ⚠ PostgreSQL not running - start it first with: bash startup.sh dev"
    exit 1
fi

echo -e "\n${YELLOW}4. Removing Coder workspace images...${NC}"
docker images | grep "localhost:5000/computor-workspace" | awk '{print $3}' | xargs -r docker rmi -f 2>/dev/null
docker images | grep "coder" | grep "workspace" | awk '{print $3}' | xargs -r docker rmi -f 2>/dev/null
echo "  ✓ Images removed"

echo -e "\n${YELLOW}5. Clearing Coder registry data...${NC}"
# Remove any registry data that might be cached
docker exec docker-postgres-1 psql -U $POSTGRES_USER -c "DROP DATABASE IF EXISTS coder_registry WITH (FORCE);" 2>/dev/null
docker system prune -f 2>/dev/null
echo "  ✓ Registry cleared"

echo -e "\n${GREEN}✓ COMPLETE Coder wipe finished!${NC}"
echo ""
echo "Next steps:"
echo "1. Restart services: bash startup.sh dev --coder"
echo "2. Coder will be completely fresh - new database, new admin user"
echo "3. Admin will be created with credentials from .env:"
echo "   - Email: $CODER_ADMIN_EMAIL"
echo "   - Password: $CODER_ADMIN_PASSWORD"
echo ""
echo "NOTE: Make sure .env has the credentials you want BEFORE restarting!"