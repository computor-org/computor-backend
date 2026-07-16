#!/bin/bash

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/ops/lib/common.sh"

echo -e "${RED}=== CODER DATA WIPE SCRIPT ===${NC}"
echo -e "${YELLOW}WARNING: This will permanently delete all Coder data!${NC}"
echo ""
read -p "Are you sure you want to wipe all Coder data? Type 'yes' to confirm: " confirmation

if [ "$confirmation" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

load_env
detect_environment || ENVIRONMENT="dev"
derive_public_urls "$ENVIRONMENT"
pin_project_name
CODER_DETECTED=true   # always include the coder overlay — that's what we wipe
assemble_compose_files "$ENVIRONMENT"

echo -e "\n${YELLOW}Stopping all Coder services via docker compose...${NC}"
compose stop coder-postgres coder coder-registry temporal-worker-coder 2>/dev/null
compose rm -f coder-postgres coder coder-registry temporal-worker-coder 2>/dev/null

echo -e "\n${YELLOW}Removing Coder workspace containers...${NC}"
# Workspace containers carry the coder.owner label (set by the Terraform template)
docker ps -aq --filter "label=coder.owner" | xargs -r docker rm -f 2>/dev/null

echo -e "\n${YELLOW}Removing Coder Docker volumes...${NC}"
docker volume rm -f computor-coder-home computor-coder-registry 2>/dev/null
# Legacy per-workspace home volumes (labelled by Terraform) ...
docker volume ls -q --filter "label=coder.owner" | xargs -r docker volume rm -f 2>/dev/null
# ... and shared per-user home volumes (engine-created, unlabelled: coder-home-<owner-id>)
docker volume ls -q --filter "name=coder-home-" | xargs -r docker volume rm -f 2>/dev/null

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
echo "  2. Start services: ./computor.sh up dev -d"
echo "  3. Coder will recreate its database and admin user automatically"
echo "  4. Build images and push templates via admin API:"
echo "     POST /coder/admin/images/build"
echo "     POST /coder/admin/templates/push"
echo ""
echo "Note: User workspace data in Docker volumes has been deleted."
echo "      Templates in \${SYSTEM_DEPLOYMENT_PATH}/coder/templates/ are preserved."
