#!/bin/bash

# Computor maintenance mode script
#
# Provides two levels of maintenance:
#   1. API-level: Use the /system/maintenance/activate API endpoint
#      (blocks non-GET requests for non-admins, services stay running)
#   2. Full maintenance: Use this script
#      (stops API/web/temporal, keeps Traefik + static-server + Redis)
#
# Usage:
#   ./maintenance.sh enter [dev|prod]     Enter full maintenance mode
#   ./maintenance.sh exit [dev|prod]      Exit maintenance mode
#   ./maintenance.sh status               Check maintenance state

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
OPS_DIR="${SCRIPT_DIR}/ops"

# Load environment
if [ -f "${SCRIPT_DIR}/.env" ]; then
    set -a
    source "${SCRIPT_DIR}/.env"
    set +a
else
    echo -e "${RED}No .env file found!${NC}"
    exit 1
fi

ACTION="${1:-status}"
ENVIRONMENT="${2:-prod}"

# Traefik dynamic config directory
TRAEFIK_DYNAMIC_DIR="${SYSTEM_DEPLOYMENT_PATH}/traefik/dynamic"
MAINTENANCE_CONFIG="${TRAEFIK_DYNAMIC_DIR}/maintenance.yaml"
MAINTENANCE_PAGE_DIR="${SYSTEM_DEPLOYMENT_PATH}/shared/documents/_maintenance"

# Build compose files string (same logic as startup.sh/stop.sh)
COMPOSE_FILES="-f ${OPS_DIR}/docker/docker-compose.base.yaml -f ${OPS_DIR}/docker/docker-compose.${ENVIRONMENT}.yaml"
if [ "$ENVIRONMENT" = "prod" ]; then
    COMPOSE_FILES="$COMPOSE_FILES -f ${OPS_DIR}/docker/docker-compose.web.yaml"
fi
if [ "$CODER_ENABLED" = "true" ]; then
    COMPOSE_FILES="$COMPOSE_FILES -f ${OPS_DIR}/docker/docker-compose.coder.yaml"
fi

# Services to KEEP running during maintenance
KEEP_SERVICES="traefik static-server redis"

ensure_maintenance_page() {
    mkdir -p "$MAINTENANCE_PAGE_DIR"
    if [ ! -f "$MAINTENANCE_PAGE_DIR/index.html" ]; then
        cp "${SCRIPT_DIR}/ops/maintenance/maintenance.html" "$MAINTENANCE_PAGE_DIR/index.html" 2>/dev/null || \
        cat > "$MAINTENANCE_PAGE_DIR/index.html" << 'HTMLEOF'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Computor - Maintenance</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh;display:flex;align-items:center;justify-content:center}
        .container{text-align:center;padding:2rem;max-width:600px}
        .icon{font-size:4rem;margin-bottom:1rem}
        h1{font-size:2rem;margin-bottom:.5rem;color:#f8fafc}
        .subtitle{font-size:1.1rem;color:#94a3b8;margin-bottom:2rem}
        .message{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:1.5rem;margin-bottom:2rem}
        .status{display:inline-block;background:#f59e0b;color:#0f172a;padding:.25rem .75rem;border-radius:9999px;font-size:.875rem;font-weight:600}
        .refresh{color:#60a5fa;cursor:pointer;text-decoration:underline;background:none;border:none;font-size:1rem;margin-top:1rem}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">&#9881;</div>
        <h1>Scheduled Maintenance</h1>
        <p class="subtitle">Computor is currently undergoing planned maintenance</p>
        <div class="message">
            <p>We are performing system updates to improve your experience. The platform will be back online shortly.</p>
        </div>
        <span class="status">Maintenance in Progress</span>
        <br>
        <button class="refresh" onclick="location.reload()">Check again</button>
    </div>
</body>
</html>
HTMLEOF
        echo -e "  ${GREEN}Created maintenance page${NC}"
    fi
}

activate_traefik_maintenance() {
    mkdir -p "$TRAEFIK_DYNAMIC_DIR"
    cat > "$MAINTENANCE_CONFIG" << 'YAMLEOF'
http:
  routers:
    maintenance-catchall:
      rule: "PathPrefix(`/`)"
      entrypoints:
        - web
      priority: 9999
      service: maintenance-page
      middlewares:
        - maintenance-rewrite

  middlewares:
    maintenance-rewrite:
      replacePath:
        path: "/_maintenance/index.html"

  services:
    maintenance-page:
      loadBalancer:
        servers:
          - url: "http://static-server:8080"
YAMLEOF
    echo -e "  ${GREEN}Traefik maintenance route activated${NC}"
}

deactivate_traefik_maintenance() {
    if [ -f "$MAINTENANCE_CONFIG" ]; then
        rm -f "$MAINTENANCE_CONFIG"
        echo -e "  ${GREEN}Traefik maintenance route removed${NC}"
    fi
}

set_redis_maintenance() {
    local active="$1"
    local message="$2"

    if [ "$active" = "1" ]; then
        docker compose $COMPOSE_FILES exec -T redis redis-cli \
            -a "$REDIS_PASSWORD" \
            HSET "maintenance:state" \
            active "1" \
            message "$message" \
            activated_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
            activated_by "maintenance_script" \
            2>/dev/null
        echo -e "  ${GREEN}Redis maintenance state: ACTIVE${NC}"
    else
        docker compose $COMPOSE_FILES exec -T redis redis-cli \
            -a "$REDIS_PASSWORD" \
            DEL "maintenance:state" "maintenance:schedule" \
            2>/dev/null
        echo -e "  ${GREEN}Redis maintenance state: CLEARED${NC}"
    fi
}

get_stoppable_services() {
    # List all services minus the ones we want to keep
    docker compose $COMPOSE_FILES config --services 2>/dev/null | while read service; do
        local keep=false
        for keep_svc in $KEEP_SERVICES; do
            if [ "$service" = "$keep_svc" ]; then
                keep=true
                break
            fi
        done
        if [ "$keep" = false ]; then
            echo "$service"
        fi
    done
}

case "$ACTION" in
    enter)
        echo -e "${YELLOW}=== Entering Full Maintenance Mode ===${NC}"
        echo -e "Environment: ${BLUE}$ENVIRONMENT${NC}"

        # Step 1: Set Redis maintenance state (API middleware starts blocking)
        echo -e "\n${GREEN}Step 1: Setting maintenance state in Redis...${NC}"
        set_redis_maintenance "1" "The system is undergoing scheduled maintenance. Please try again later."

        # Step 2: Wait for middleware caches to expire
        echo -e "\n${GREEN}Step 2: Waiting for middleware cache to expire (3s)...${NC}"
        sleep 3

        # Step 3: Ensure maintenance page exists
        echo -e "\n${GREEN}Step 3: Ensuring maintenance page exists...${NC}"
        ensure_maintenance_page

        # Step 4: Activate Traefik maintenance routing
        echo -e "\n${GREEN}Step 4: Activating Traefik maintenance route...${NC}"
        activate_traefik_maintenance

        # Step 5: Stop application services (keep infrastructure)
        echo -e "\n${GREEN}Step 5: Stopping application services...${NC}"
        SERVICES_TO_STOP=$(get_stoppable_services)
        for service in $SERVICES_TO_STOP; do
            docker compose $COMPOSE_FILES stop "$service" 2>/dev/null && \
                echo -e "  Stopped: ${YELLOW}$service${NC}" || true
        done

        echo -e "\n${GREEN}=== Full Maintenance Mode Active ===${NC}"
        echo -e "Services still running: ${BLUE}$KEEP_SERVICES${NC}"
        echo -e "All HTTP traffic is routed to the maintenance page."
        echo -e "\nTo exit: ${GREEN}./maintenance.sh exit $ENVIRONMENT${NC}"
        ;;

    exit)
        echo -e "${GREEN}=== Exiting Maintenance Mode ===${NC}"
        echo -e "Environment: ${BLUE}$ENVIRONMENT${NC}"

        # Step 1: Remove Traefik maintenance routing
        echo -e "\n${GREEN}Step 1: Removing Traefik maintenance route...${NC}"
        deactivate_traefik_maintenance

        # Step 2: Start all services
        echo -e "\n${GREEN}Step 2: Starting all services...${NC}"
        docker compose $COMPOSE_FILES up -d

        # Step 3: Wait for services to be healthy
        echo -e "\n${GREEN}Step 3: Waiting for services to start (10s)...${NC}"
        sleep 10

        # Step 4: Clear Redis maintenance state
        echo -e "\n${GREEN}Step 4: Clearing maintenance state in Redis...${NC}"
        set_redis_maintenance "0" ""

        echo -e "\n${GREEN}=== Maintenance Mode Exited ===${NC}"
        echo -e "All services are running. Full access restored."
        ;;

    status)
        echo -e "${BLUE}=== Maintenance Status ===${NC}"

        # Check Redis state
        MAINT_STATE=$(docker compose $COMPOSE_FILES exec -T redis redis-cli \
            -a "$REDIS_PASSWORD" \
            HGET "maintenance:state" active 2>/dev/null || echo "unknown")

        if [ "$MAINT_STATE" = "1" ]; then
            echo -e "Maintenance mode: ${YELLOW}ACTIVE${NC}"
            MAINT_MSG=$(docker compose $COMPOSE_FILES exec -T redis redis-cli \
                -a "$REDIS_PASSWORD" \
                HGET "maintenance:state" message 2>/dev/null)
            echo -e "Message: ${MAINT_MSG}"
        else
            echo -e "Maintenance mode: ${GREEN}INACTIVE${NC}"
        fi

        # Check Traefik config
        if [ -f "$MAINTENANCE_CONFIG" ]; then
            echo -e "Traefik maintenance route: ${YELLOW}ACTIVE${NC}"
        else
            echo -e "Traefik maintenance route: ${GREEN}INACTIVE${NC}"
        fi

        # Check scheduled maintenance
        SCHED=$(docker compose $COMPOSE_FILES exec -T redis redis-cli \
            -a "$REDIS_PASSWORD" \
            HGET "maintenance:schedule" scheduled_at 2>/dev/null || echo "")
        if [ -n "$SCHED" ] && [ "$SCHED" != "(nil)" ]; then
            echo -e "Scheduled maintenance: ${YELLOW}$SCHED${NC}"
        else
            echo -e "Scheduled maintenance: ${GREEN}none${NC}"
        fi

        # Show running services
        echo -e "\n${BLUE}Running services:${NC}"
        docker compose $COMPOSE_FILES ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null || \
            echo "  Unable to query services"
        ;;

    *)
        echo "Usage: $0 {enter|exit|status} [dev|prod]"
        echo ""
        echo "Commands:"
        echo "  enter [env]   Enter full maintenance mode (stop API/web, keep proxy)"
        echo "  exit [env]    Exit maintenance mode (start all services)"
        echo "  status        Show current maintenance state"
        echo ""
        echo "For API-level maintenance (no downtime for reads):"
        echo "  POST /system/maintenance/activate   Activate via API"
        echo "  POST /system/maintenance/deactivate Deactivate via API"
        exit 1
        ;;
esac
