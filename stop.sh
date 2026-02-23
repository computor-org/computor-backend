#!/bin/bash

# Computor stop script
# Coder support is controlled via CODER_ENABLED in .env
# Usage:
#   ./stop.sh [dev|prod] [docker-compose-options]
#   ./stop.sh dev             # Stop development services
#   ./stop.sh prod            # Stop production services
#   ./stop.sh                 # Stop last used configuration

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
OPS_DIR="${SCRIPT_DIR}/ops"

# Default values
ENVIRONMENT=""
DOCKER_ARGS=""
REMOVE_VOLUMES=false

# Try to detect last used configuration from running services
detect_running_config() {
    # Check if any services are running
    if ! docker ps --format "table {{.Names}}" | grep -q "computor"; then
        return 1
    fi

    # Try to detect environment by checking which services are running
    if docker ps --format "{{.Names}}" | grep -q "computor-minio"; then
        # Base services are running

        # Check for dev-specific service (temporal-ui)
        if docker ps --format "{{.Names}}" | grep -q "temporal-ui"; then
            ENVIRONMENT="dev"
        # Check for prod-specific service (uvicorn or frontend)
        elif docker ps --format "{{.Names}}" | grep -q "uvicorn\|frontend"; then
            ENVIRONMENT="prod"
        else
            # Default to dev if we can't determine
            ENVIRONMENT="dev"
        fi

        # Check if Coder is running
        if docker ps --format "{{.Names}}" | grep -q "computor-coder"; then
            CODER_DETECTED=true
        fi

        return 0
    fi

    return 1
}

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
        -v|--volumes)
            echo -e "${RED}ERROR: The -v/--volumes flag is disabled for safety!${NC}"
            echo ""
            echo "To remove volumes safely, use the dedicated cleanup scripts:"
            echo "  ${GREEN}./wipe-coder-complete.sh${NC}  - Wipe all Coder data (database, volumes, images)"
            echo "  ${GREEN}./wipe-coder.sh${NC}           - Quick Coder cleanup"
            echo ""
            echo "These scripts will NEVER touch your main infrastructure (Postgres, MinIO, Redis)."
            echo ""
            exit 1
            ;;
        --help|-h)
            echo "Usage: $0 [environment] [options]"
            echo ""
            echo "Environments:"
            echo "  dev, development    Stop development services"
            echo "  prod, production    Stop production services"
            echo ""
            echo "Options:"
            echo "  --help, -h         Show this help message"
            echo ""
            echo "Coder services are included automatically when CODER_ENABLED=true in .env."
            echo ""
            echo "Examples:"
            echo "  $0                 Stop services (auto-detect configuration)"
            echo "  $0 dev             Stop development services"
            echo ""
            echo "To remove Coder data safely (without touching main infrastructure):"
            echo "  ./wipe-coder-complete.sh  - Complete Coder wipe (database, volumes, images)"
            echo "  ./wipe-coder.sh           - Quick Coder cleanup"
            exit 0
            ;;
        *)
            # Collect remaining arguments for docker-compose
            DOCKER_ARGS="$DOCKER_ARGS $1"
            shift
            ;;
    esac
done

echo -e "${GREEN}=== Computor Stop Script ===${NC}"

# If no environment specified, try to detect
if [ -z "$ENVIRONMENT" ]; then
    echo -e "${BLUE}Detecting running configuration...${NC}"

    if detect_running_config; then
        echo -e "  Detected: ${YELLOW}$ENVIRONMENT${NC} environment"
        if [ "$CODER_DETECTED" = true ]; then
            echo -e "  Coder: ${YELLOW}running${NC}"
        fi
    else
        echo -e "${YELLOW}No running Computor services detected or unable to determine configuration.${NC}"
        echo -e "Please specify the environment:"
        echo -e "  ${GREEN}$0 dev${NC}    # For development"
        echo -e "  ${GREEN}$0 prod${NC}   # For production"
        exit 1
    fi
else
    echo -e "Environment: ${YELLOW}$ENVIRONMENT${NC}"
fi

# Load environment file
if [ -f .env ]; then
    echo -e "\n${GREEN}Loading environment file...${NC}"
    set -a
    source .env && echo "  ✓ .env loaded"
    set +a
else
    echo -e "\n${YELLOW}Warning: No .env file found${NC}"
    echo "Some features may not work correctly without environment variables."
fi

# Determine if Coder compose file should be included
# Use CODER_ENABLED from .env, or auto-detected running Coder containers
INCLUDE_CODER=false
if [ "$CODER_ENABLED" = "true" ] || [ "$CODER_DETECTED" = true ]; then
    INCLUDE_CODER=true
fi

echo -e "Coder: ${YELLOW}$([ "$INCLUDE_CODER" = true ] && echo "enabled" || echo "disabled")${NC}"

# Build docker-compose command (must match startup.sh)
COMPOSE_FILES="-f ${OPS_DIR}/docker/docker-compose.base.yaml -f ${OPS_DIR}/docker/docker-compose.$ENVIRONMENT.yaml"
if [ "$ENVIRONMENT" = "prod" ]; then
    COMPOSE_FILES="$COMPOSE_FILES -f ${OPS_DIR}/docker/docker-compose.web.yaml"
fi
if [ "$INCLUDE_CODER" = true ]; then
    COMPOSE_FILES="$COMPOSE_FILES -f ${OPS_DIR}/docker/docker-compose.coder.yaml"
fi

# Show what will be stopped
echo -e "\n${BLUE}Services to stop:${NC}"
docker compose $COMPOSE_FILES ps --services | while read service; do
    echo "  • $service"
done

# Stop services
echo -e "\n${GREEN}Stopping services...${NC}"
docker compose $COMPOSE_FILES down $DOCKER_ARGS

# Show result
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✓ Services stopped successfully${NC}"

    # Show how to start again
    echo -e "\n${BLUE}To start services again:${NC}"
    echo -e "  ${GREEN}./startup.sh $ENVIRONMENT -d${NC}"
else
    echo -e "\n${RED}✗ Failed to stop services${NC}"
    echo -e "Check the error messages above for details."
    exit 1
fi

# Optional: Clean up dangling images and volumes
echo -e "\n${BLUE}Tip:${NC} To clean up unused Docker resources:"
echo -e "  ${YELLOW}docker system prune -f${NC}     # Remove unused containers/networks/images"
echo -e "  ${YELLOW}docker volume prune -f${NC}      # Remove unused volumes"