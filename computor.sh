#!/bin/bash
#
# Computor lifecycle CLI — the single entrypoint for operating the stack.
#
# Usage:
#   ./computor.sh up   [dev|prod] [docker-compose-options]   # start the stack
#   ./computor.sh down [dev|prod] [docker-compose-options]   # stop the stack (auto-detects env)
#   ./computor.sh status [dev|prod]                          # services + maintenance state
#   ./computor.sh maintenance enter|exit|status [dev|prod]   # full maintenance mode
#   ./computor.sh update check|status|run|exec [prod]        # self-update (see ops/lib/update.sh)
#   ./computor.sh test [--unit|--integration|--slow|--file <name>] [pytest-args]
#                                                            # backend test suite (pytest)
#
# Examples:
#   ./computor.sh up dev -d
#   ./computor.sh up prod --build -d
#   ./computor.sh down
#   ./computor.sh maintenance enter prod
#   ./computor.sh test --unit

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/ops/lib/common.sh"

usage() {
    # Print the header comment block (skipping the shebang) as help text.
    awk 'NR > 1 && /^#/ { sub(/^# ?/, ""); print; next } NR > 1 { exit }' "${BASH_SOURCE[0]}"
    exit "${1:-1}"
}

# Shared argv parsing: extracts an optional dev/prod token, collects the rest
# into DOCKER_ARGS (pass-through to docker compose).
parse_env_args() {
    DOCKER_ARGS=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            dev|development)  ENVIRONMENT="dev" ;;
            prod|production)  ENVIRONMENT="prod" ;;
            *)                DOCKER_ARGS="$DOCKER_ARGS $1" ;;
        esac
        shift
    done
}

create_dir_if_needed() {
    local dir_path="$1"
    if [ ! -d "$dir_path" ]; then
        echo "  Creating: $dir_path"
        mkdir -p "$dir_path" || die "  Failed to create $dir_path"
    fi
}

# Ensure SYSTEM_DEPLOYMENT_PATH exists and is writable by the current user.
# We do NOT run the whole script as root, and we NEVER touch a pre-existing,
# writable base — whatever permissions/ownership you gave it are left exactly
# as-is. We only escalate (after asking) when the base has to be created under a
# root-owned path like /srv, or exists but isn't writable at all. A base we
# create ourselves is chown'd to you rather than chmod 777'd.
ensure_deployment_base() {
    local base="$SYSTEM_DEPLOYMENT_PATH"

    if [ -e "$base" ] && [ ! -d "$base" ]; then
        die "  '$base' exists but is not a directory."
    fi

    # Pre-existing and writable -> use it untouched (your permissions stay).
    if [ -d "$base" ] && [ -w "$base" ]; then
        return 0
    fi
    # Missing -> create unprivileged if the parent allows it.
    if [ ! -d "$base" ] && mkdir -p "$base" 2>/dev/null; then
        return 0
    fi

    # Either missing under a root-owned parent, or exists but not writable by us.
    if [ -d "$base" ]; then
        warn "  '$base' exists but is not writable by $(id -un)."
    else
        warn "  '$base' is under a root-owned path and must be created."
    fi
    if ! command -v sudo >/dev/null 2>&1; then
        log "${RED}  sudo is not available.${NC} Prepare it manually, then re-start:"
        log "    sudo mkdir -p '$base' && sudo chown -R $(id -u):$(id -g) '$base'"
        exit 1
    fi

    local reply
    read -rp "  Create/own '$base' with sudo now? [y/N] " reply
    case "$reply" in
        [yY]|[yY][eE][sS])
            sudo mkdir -p "$base" \
                && sudo chown -R "$(id -u):$(id -g)" "$base" \
                || die "  Failed to prepare $base."
            log "  ${GREEN}Prepared $base.${NC}"
            ;;
        *)
            log "${RED}  Aborted.${NC} Prepare it manually, then re-start:"
            log "    sudo mkdir -p '$base' && sudo chown -R $(id -u):$(id -g) '$base'"
            exit 1
            ;;
    esac
}

# Verify a non-root container can reach the Docker socket and export DOCKER_GID.
# Needed by Coder's provisioner (workspace builds) and the updater sidecar.
# The socket's group must be probed INSIDE a container — host-side stat is wrong
# on Docker Desktop / OrbStack, where the in-container socket is root:root.
verify_docker_socket_access() {
    log "\n${GREEN}Checking Docker socket access...${NC}"

    if ! docker info >/dev/null 2>&1; then
        die "ERROR: Docker daemon is not reachable.
  Start Docker/OrbStack and re-run."
    fi

    local sock_gid
    sock_gid=$(docker run --rm -v /var/run/docker.sock:/var/run/docker.sock alpine \
        stat -c '%g' /var/run/docker.sock 2>/dev/null)

    if [ -z "${DOCKER_GID:-}" ]; then
        if [ -n "$sock_gid" ]; then
            DOCKER_GID="$sock_gid"
            echo "  Detected DOCKER_GID=$DOCKER_GID"
        else
            die "ERROR: Could not detect the Docker socket group.
  Set DOCKER_GID in .env to the gid of /var/run/docker.sock inside a container."
        fi
    else
        echo "  Using DOCKER_GID=$DOCKER_GID (from .env)"
        if [ -n "$sock_gid" ] && [ "$DOCKER_GID" != "$sock_gid" ]; then
            warn "  Note: socket gid inside a container is $sock_gid but DOCKER_GID=$DOCKER_GID."
        fi
    fi
    export DOCKER_GID

    # End-to-end: a non-root container joined to DOCKER_GID must be able to
    # write (i.e. connect) to the socket. This catches a wrong gid before the
    # first workspace build / update run fails with "permission denied".
    if ! docker run --rm --user 1000:1000 --group-add "$DOCKER_GID" \
            -v /var/run/docker.sock:/var/run/docker.sock alpine \
            test -w /var/run/docker.sock >/dev/null 2>&1; then
        die "ERROR: a non-root container in group $DOCKER_GID still cannot access /var/run/docker.sock.
  Set DOCKER_GID=${sock_gid:-<gid of docker.sock inside a container>} in .env and re-run."
    fi
    log "  ${GREEN}OK — non-root container can reach the Docker socket (gid $DOCKER_GID).${NC}"
}

cmd_up() {
    ENVIRONMENT="dev"
    parse_env_args "$@"

    log "${GREEN}=== Computor Startup ===${NC}"
    log "Environment: ${YELLOW}$ENVIRONMENT${NC}"

    log "\n${GREEN}Loading environment file...${NC}"
    load_env && echo "  ✓ .env"
    derive_public_urls "$ENVIRONMENT"
    [ -n "${NEXT_PUBLIC_API_URL:-}" ] && [ "$ENVIRONMENT" = "prod" ] \
        && log "  ${GREEN}✓${NC} Derived public URLs from PUBLIC_DOMAIN=${PUBLIC_DOMAIN}"

    # Ensure the shared Forgejo<->Keycloak client secret exists and is persisted
    # in .env. It must be stable (the realm import and the compose env have to
    # agree on one value) and is only needed when both Keycloak and Forgejo are
    # enabled. This self-heals .env files created before the secret existed.
    if [ "${KEYCLOAK_ENABLED:-}" = "true" ] && [ "${GIT_SERVER:-}" = "forgejo" ] && [ -z "${FORGEJO_KEYCLOAK_CLIENT_SECRET:-}" ]; then
        FORGEJO_KEYCLOAK_CLIENT_SECRET=$(openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | xxd -p -c 256)
        sed -i.bak '/^FORGEJO_KEYCLOAK_CLIENT_SECRET=/d' "${REPO_ROOT}/.env" && rm -f "${REPO_ROOT}/.env.bak"
        printf 'FORGEJO_KEYCLOAK_CLIENT_SECRET=%s\n' "$FORGEJO_KEYCLOAK_CLIENT_SECRET" >> "${REPO_ROOT}/.env"
        export FORGEJO_KEYCLOAK_CLIENT_SECRET
        log "  ${GREEN}✓${NC} Generated and persisted FORGEJO_KEYCLOAK_CLIENT_SECRET to .env"
    fi

    pin_project_name
    assemble_compose_files "$ENVIRONMENT"
    print_stack_summary "$ENVIRONMENT"

    # Pre-create directories
    log "\n${GREEN}Creating necessary directories...${NC}"
    : "${SYSTEM_DEPLOYMENT_PATH:?SYSTEM_DEPLOYMENT_PATH must be set in .env}"
    ensure_deployment_base

    create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/postgres"
    create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/temporal-postgres"
    create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/redis"
    create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/redis-data"
    create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/minio/data"
    create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/shared"
    for dir in documents courses course-contents defaults repositories; do
        create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/shared/$dir"
    done
    create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/traefik/dynamic"

    # Clear stale maintenance mode config (if services are starting, maintenance is over)
    if [ -f "${SYSTEM_DEPLOYMENT_PATH}/traefik/dynamic/maintenance.yaml" ]; then
        warn "  Clearing stale maintenance mode config"
        rm -f "${SYSTEM_DEPLOYMENT_PATH}/traefik/dynamic/maintenance.yaml"
    fi

    # Coder directories + templates (if enabled)
    if [ "${CODER_ENABLED:-}" = "true" ]; then
        create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/coder"
        create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/coder/home"
        # Coder container runs as UID 1000 — ensure it can write to its home directory
        chmod 777 "${SYSTEM_DEPLOYMENT_PATH}/coder/home" 2>/dev/null || true
        create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/coder/registry"
        create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/coder/templates"

        # Seed/sync default templates from repo. Deployed template dirs carrying a
        # .computor-managed marker are re-synced from the repo on every startup so
        # template changes actually propagate; dirs WITHOUT the marker (operator-
        # customized, or seeded before markers existed) are never touched — delete
        # such a dir once to adopt syncing.
        if [ -d "${OPS_DIR}/coder/templates" ]; then
            log "  ${GREEN}Seeding Coder templates...${NC}"
            for tpl_dir in "${OPS_DIR}/coder/templates"/*/; do
                tpl_name=$(basename "$tpl_dir")
                deployed_dir="${SYSTEM_DEPLOYMENT_PATH}/coder/templates/${tpl_name}"
                if [ ! -d "$deployed_dir" ]; then
                    echo "    Copying template: ${tpl_name}"
                    cp -r "$tpl_dir" "$deployed_dir"
                    touch "$deployed_dir/.computor-managed"
                elif [ -f "$deployed_dir/.computor-managed" ]; then
                    echo "    Syncing managed template: ${tpl_name}"
                    rm -rf "$deployed_dir"
                    cp -r "$tpl_dir" "$deployed_dir"
                    touch "$deployed_dir/.computor-managed"
                else
                    warn "    Template ${tpl_name} is unmanaged (no .computor-managed marker) — left as-is."
                    echo "      Delete ${deployed_dir} once to adopt automatic syncing."
                fi
            done
        fi
    fi

    # Docker socket access is needed by Coder (workspace provisioning) and by
    # the updater sidecar (self-update builds).
    if [ "${CODER_ENABLED:-}" = "true" ] \
        || { [ "${UPDATE_ENABLED:-}" = "true" ] && [ "$ENVIRONMENT" = "prod" ]; }; then
        verify_docker_socket_access
    fi

    # Copy defaults if source exists
    if [ -d "${REPO_ROOT}/computor-backend/src/defaults" ]; then
        log "\n${GREEN}Copying default files...${NC}"
        cp -r "${REPO_ROOT}/computor-backend/src/defaults/"* "${SYSTEM_DEPLOYMENT_PATH}/shared/defaults/" 2>/dev/null || true
    fi

    # Optional: Create Forgejo directories if enabled
    if [ "${GIT_SERVER:-}" = "forgejo" ]; then
        create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/forgejo/postgres"
        create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/forgejo/data"
    fi

    # Optional: Keycloak directories + realm/theme/IdP staging
    if [ "${KEYCLOAK_ENABLED:-}" = "true" ]; then
        log "\n${GREEN}Setting up Keycloak directories...${NC}"
        create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/keycloak-db"
        create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/keycloak/imports"
        create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/keycloak/themes"

        # Copy realm config, substituting the client secrets from .env. Both placeholders
        # are hex (no '/'), so the /-delimited sed is safe. PLACEHOLDER_CLIENT_SECRET is not
        # a substring of PLACEHOLDER_FORGEJO_CLIENT_SECRET, so the two never collide.
        if [ -f "${REPO_ROOT}/data/keycloak/computor-realm.json" ]; then
            echo "  Writing Keycloak realm configuration (substituting client secrets)..."
            sed -e "s/PLACEHOLDER_CLIENT_SECRET/${KEYCLOAK_CLIENT_SECRET}/g" \
                -e "s/PLACEHOLDER_FORGEJO_CLIENT_SECRET/${FORGEJO_KEYCLOAK_CLIENT_SECRET}/g" \
                "${REPO_ROOT}/data/keycloak/computor-realm.json" \
                > "${SYSTEM_DEPLOYMENT_PATH}/keycloak/imports/computor-realm.json"
        fi

        # Sync custom login theme(s) into the mounted themes directory
        if [ -d "${REPO_ROOT}/data/keycloak/themes" ]; then
            echo "  Syncing Keycloak themes..."
            cp -r "${REPO_ROOT}/data/keycloak/themes/." "${SYSTEM_DEPLOYMENT_PATH}/keycloak/themes/"
        fi

        # Brokered external identity providers (optional). The real provider list is
        # local-only (gitignored), like .env: seed it from the committed example on
        # first run, then stage it to the deploy path where the keycloak-idp-setup
        # one-shot reads it. Secrets are NOT in this file — they stay in .env.
        create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/keycloak/idp"
        if [ ! -f "${REPO_ROOT}/data/keycloak/identity-providers.json" ] && [ -f "${REPO_ROOT}/data/keycloak/identity-providers.example.json" ]; then
            echo "  Seeding data/keycloak/identity-providers.json from example (edit it to add providers)..."
            cp "${REPO_ROOT}/data/keycloak/identity-providers.example.json" "${REPO_ROOT}/data/keycloak/identity-providers.json"
        fi
        if [ -f "${REPO_ROOT}/data/keycloak/identity-providers.json" ]; then
            cp "${REPO_ROOT}/data/keycloak/identity-providers.json" "${SYSTEM_DEPLOYMENT_PATH}/keycloak/idp/identity-providers.json"
        fi
    fi

    # Bootstrap deployments (data/deployments/*.yaml). Applied idempotently by the API
    # at startup to seed system services (the default testing worker). Real files are
    # local-only (gitignored), like .env: seed the default from its committed example
    # on first run, then stage real (non-example) files to the deploy path where the
    # prod uvicorn container reads them (DEPLOYMENTS_DIR). In dev the host API reads
    # ./data/deployments directly. Tokens come from .env via ${VAR}, never these files.
    create_dir_if_needed "${SYSTEM_DEPLOYMENT_PATH}/deployments"
    if [ ! -f "${REPO_ROOT}/data/deployments/testing-worker.yaml" ] && [ -f "${REPO_ROOT}/data/deployments/testing-worker.example.yaml" ]; then
        echo "  Seeding data/deployments/testing-worker.yaml from example..."
        cp "${REPO_ROOT}/data/deployments/testing-worker.example.yaml" "${REPO_ROOT}/data/deployments/testing-worker.yaml"
    fi
    if [ ! -f "${REPO_ROOT}/data/deployments/example-repository.yaml" ] && [ -f "${REPO_ROOT}/data/deployments/example-repository.example.yaml" ]; then
        echo "  Seeding data/deployments/example-repository.yaml from example..."
        cp "${REPO_ROOT}/data/deployments/example-repository.example.yaml" "${REPO_ROOT}/data/deployments/example-repository.yaml"
    fi
    for f in "${REPO_ROOT}/data/deployments/"*.yaml "${REPO_ROOT}/data/deployments/"*.yml; do
        [ -f "$f" ] || continue
        case "$f" in *.example.yaml | *.example.yml) continue ;; esac
        cp "$f" "${SYSTEM_DEPLOYMENT_PATH}/deployments/"
    done

    # Make postgres init script executable. Tolerate a deploy user who is not the
    # file owner (the file ships executable from git, so this is only a touch-up).
    if [ -f "${REPO_ROOT}/docker/postgres-init/01-create-multiple-databases.sh" ]; then
        chmod +x "${REPO_ROOT}/docker/postgres-init/01-create-multiple-databases.sh" 2>/dev/null || true
    fi

    # Build provenance for image builds: baked into computor-base (ARG) and the
    # web image's NEXT_PUBLIC_GIT_COMMIT; also interpolated by compose builds.
    git_build_meta

    # The Python service images (api + temporal workers) inherit from a shared base
    # image (docker/base/Dockerfile); the matlab worker COPYs from it. Build it first
    # so their `FROM computor-base:latest` resolves. Rebuild when --build is requested
    # or when the image is missing (cached/fast otherwise).
    if [[ "$DOCKER_ARGS" == *"--build"* ]] || ! docker image inspect computor-base:latest >/dev/null 2>&1; then
        log "\n${GREEN}Building shared base image (computor-base)...${NC}"
        echo "  Baking build provenance: commit=${GIT_COMMIT} branch=${GIT_BRANCH}"
        (cd "$REPO_ROOT" && docker build -f docker/base/Dockerfile -t computor-base:latest \
            --build-arg GIT_COMMIT="$GIT_COMMIT" --build-arg GIT_BRANCH="$GIT_BRANCH" .)
    fi
    # The testing worker also layers on a heavy, slow-changing language-runtimes
    # image (Octave/R/Python 3.13/Julia) built independently of the project source.
    # Cached after the first build (no project files in its context).
    if [[ "$DOCKER_ARGS" == *"--build"* ]] || ! docker image inspect computor-testing-runtimes:latest >/dev/null 2>&1; then
        log "\n${GREEN}Building testing runtimes image (computor-testing-runtimes)...${NC}"
        (cd "$REPO_ROOT" && docker build -f docker/testing-runtimes/Dockerfile -t computor-testing-runtimes:latest .)
    fi
    # The coder worker likewise layers its system packages (Docker CLI + coder CLI)
    # in an independent image so a project source change no longer re-runs that
    # apt/curl install. Built once and cached; only needed when Coder is enabled.
    if [ "${CODER_ENABLED:-}" = "true" ] && { [[ "$DOCKER_ARGS" == *"--build"* ]] || ! docker image inspect computor-coder-runtime:latest >/dev/null 2>&1; }; then
        log "\n${GREEN}Building coder runtime image (computor-coder-runtime)...${NC}"
        (cd "$REPO_ROOT" && docker build -f docker/coder-runtime/Dockerfile -t computor-coder-runtime:latest .)
    fi
    # Code-server workspace templates build FROM computor-code-server:latest — the
    # upstream code-server image plus the webview service-worker patch (issue #274).
    # The temporal worker builds template images on this same docker daemon, so the
    # local tag resolves without a registry; build it before any template build.
    if [ "${CODER_ENABLED:-}" = "true" ] && { [[ "$DOCKER_ARGS" == *"--build"* ]] || ! docker image inspect computor-code-server:latest >/dev/null 2>&1; }; then
        log "\n${GREEN}Building patched code-server base (computor-code-server)...${NC}"
        (cd "$REPO_ROOT" && docker build -f docker/code-server-base/Dockerfile -t computor-code-server:latest docker/code-server-base)
    fi

    # Start services
    log "\n${GREEN}Starting Computor services...${NC}"
    echo "Command: docker compose $COMPOSE_FILES up $DOCKER_ARGS"
    # shellcheck disable=SC2086
    compose up $DOCKER_ARGS

    # Show status if running in detached mode
    if [[ "$DOCKER_ARGS" == *"-d"* ]]; then
        log "\n${GREEN}Services status:${NC}"
        compose ps

        log "\n${GREEN}Service URLs:${NC}"
        echo "  • API: http://localhost:${API_PORT:-8000}"
        echo "  • Traefik: http://localhost:${TRAEFIK_HTTP_PORT:-8080}"

        if [ "$ENVIRONMENT" = "prod" ]; then
            echo "  • Frontend: http://localhost:${TRAEFIK_HTTP_PORT:-8080}"
        fi

        if [ "$ENVIRONMENT" = "dev" ]; then
            echo "  • Temporal UI: http://localhost:${TEMPORAL_UI_PORT:-8088}"
            echo "  • MinIO Console: http://localhost:${MINIO_CONSOLE_PORT:-9001}"
        fi

        if [ "${CODER_ENABLED:-}" = "true" ]; then
            # Coder's server is internal-only (bound to 127.0.0.1, not behind Traefik);
            # only workspaces are exposed, via Traefik.
            echo "  • Coder API (local access only): http://localhost:7080"
            echo "  • Coder workspaces: ${CODER_WORKSPACE_BASE_URL:-http://localhost:${TRAEFIK_HTTP_PORT:-8080}/coder}"
        fi

        if [ "${GIT_SERVER:-}" = "forgejo" ]; then
            echo "  • Forgejo: http://localhost:${FORGEJO_PORT:-3030}"
        fi

        log "\n${GREEN}To stop services:${NC}"
        # Use the CLI, not raw `docker compose down`: in prod the public URLs are
        # derived from PUBLIC_DOMAIN and left empty in .env, so a bare compose
        # command fails on ${NEXT_PUBLIC_API_URL:?}. `down` re-derives them.
        echo "  ./computor.sh down $ENVIRONMENT"

        log "\n${GREEN}To view logs:${NC}"
        echo "  docker compose $COMPOSE_FILES logs -f [service-name]"
    fi
}

cmd_down() {
    ENVIRONMENT=""
    DOCKER_ARGS=""
    while [[ $# -gt 0 ]]; do
        case $1 in
            dev|development)  ENVIRONMENT="dev" ;;
            prod|production)  ENVIRONMENT="prod" ;;
            -v|--volumes)
                log "${RED}ERROR: The -v/--volumes flag is disabled for safety!${NC}"
                echo ""
                echo "To remove volumes safely, use the dedicated cleanup scripts:"
                echo -e "  ${GREEN}./wipe-coder-complete.sh${NC}  - Wipe all Coder data (database, volumes, images)"
                echo -e "  ${GREEN}./wipe-coder.sh${NC}           - Quick Coder cleanup"
                echo ""
                echo "These scripts will NEVER touch your main infrastructure (Postgres, MinIO, Redis)."
                exit 1
                ;;
            -h|--help)        usage 0 ;;
            *)                DOCKER_ARGS="$DOCKER_ARGS $1" ;;
        esac
        shift
    done

    log "${GREEN}=== Computor Stop ===${NC}"

    if [ -z "$ENVIRONMENT" ]; then
        log "${BLUE}Detecting running configuration...${NC}"
        if detect_environment; then
            log "  Detected: ${YELLOW}$ENVIRONMENT${NC} environment"
            [ "${CODER_DETECTED:-}" = "true" ] && log "  Coder: ${YELLOW}running${NC}"
        else
            warn "No running Computor services detected or unable to determine configuration."
            log "Please specify the environment:"
            log "  ${GREEN}$0 down dev${NC}    # For development"
            log "  ${GREEN}$0 down prod${NC}   # For production"
            exit 1
        fi
    else
        log "Environment: ${YELLOW}$ENVIRONMENT${NC}"
    fi

    # Tolerate a missing .env on `down` (stopping must always be possible).
    if [ -f "${REPO_ROOT}/.env" ]; then
        log "\n${GREEN}Loading environment file...${NC}"
        load_env && echo "  ✓ .env loaded"
    else
        warn "Warning: No .env file found — stopping with detected configuration only."
    fi

    derive_public_urls "$ENVIRONMENT"
    pin_project_name
    assemble_compose_files "$ENVIRONMENT"

    log "\n${BLUE}Services to stop:${NC}"
    compose ps --services | while read -r service; do
        echo "  • $service"
    done

    log "\n${GREEN}Stopping services...${NC}"
    # shellcheck disable=SC2086
    compose down $DOCKER_ARGS

    log "\n${GREEN}✓ Services stopped successfully${NC}"
    log "\n${BLUE}To start services again:${NC}"
    log "  ${GREEN}./computor.sh up $ENVIRONMENT -d${NC}"
}

maintenance_status_report() {
    log "${BLUE}=== Maintenance Status ===${NC}"

    local maint_state
    maint_state=$(redis_cli HGET "maintenance:state" active || echo "unknown")
    if [ "$maint_state" = "1" ]; then
        log "Maintenance mode: ${YELLOW}ACTIVE${NC}"
        log "Message: $(redis_cli HGET "maintenance:state" message)"
    else
        log "Maintenance mode: ${GREEN}INACTIVE${NC}"
    fi

    maintenance_paths
    if [ -f "$MAINTENANCE_CONFIG" ]; then
        log "Traefik maintenance route: ${YELLOW}ACTIVE${NC}"
    else
        log "Traefik maintenance route: ${GREEN}INACTIVE${NC}"
    fi

    local sched
    sched=$(redis_cli HGET "maintenance:schedule" scheduled_at || echo "")
    if [ -n "$sched" ] && [ "$sched" != "(nil)" ]; then
        log "Scheduled maintenance: ${YELLOW}$sched${NC}"
    else
        log "Scheduled maintenance: ${GREEN}none${NC}"
    fi
}

cmd_maintenance() {
    local action="${1:-status}"
    shift || true
    ENVIRONMENT="prod"
    parse_env_args "$@"

    load_env
    derive_public_urls "$ENVIRONMENT"
    pin_project_name
    assemble_compose_files "$ENVIRONMENT"

    case "$action" in
        enter)
            log "${YELLOW}=== Entering Full Maintenance Mode ===${NC}"
            log "Environment: ${BLUE}$ENVIRONMENT${NC}"

            log "\n${GREEN}Step 1: Setting maintenance state in Redis...${NC}"
            set_redis_maintenance "1" "The system is undergoing scheduled maintenance. Please try again later."

            log "\n${GREEN}Step 2: Waiting for middleware cache to expire (3s)...${NC}"
            sleep 3

            log "\n${GREEN}Step 3: Ensuring maintenance page exists...${NC}"
            ensure_maintenance_page

            log "\n${GREEN}Step 4: Activating Traefik maintenance route...${NC}"
            activate_traefik_maintenance

            log "\n${GREEN}Step 5: Stopping application services...${NC}"
            local service
            for service in $(get_stoppable_services); do
                compose stop "$service" 2>/dev/null \
                    && log "  Stopped: ${YELLOW}$service${NC}" || true
            done

            log "\n${GREEN}=== Full Maintenance Mode Active ===${NC}"
            log "Services still running: ${BLUE}$MAINTENANCE_KEEP_SERVICES${NC}"
            log "All HTTP traffic is routed to the maintenance page."
            log "\nTo exit: ${GREEN}./computor.sh maintenance exit $ENVIRONMENT${NC}"
            ;;

        exit)
            log "${GREEN}=== Exiting Maintenance Mode ===${NC}"
            log "Environment: ${BLUE}$ENVIRONMENT${NC}"

            log "\n${GREEN}Step 1: Removing Traefik maintenance route...${NC}"
            deactivate_traefik_maintenance

            log "\n${GREEN}Step 2: Starting all services...${NC}"
            compose up -d

            log "\n${GREEN}Step 3: Waiting for services to start (10s)...${NC}"
            sleep 10

            log "\n${GREEN}Step 4: Clearing maintenance state in Redis...${NC}"
            set_redis_maintenance "0" ""

            log "\n${GREEN}=== Maintenance Mode Exited ===${NC}"
            log "All services are running. Full access restored."
            ;;

        status)
            maintenance_status_report
            log "\n${BLUE}Running services:${NC}"
            compose ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null \
                || echo "  Unable to query services"
            ;;

        *)
            echo "Usage: $0 maintenance {enter|exit|status} [dev|prod]"
            echo ""
            echo "For API-level maintenance (no downtime for reads):"
            echo "  POST /system/maintenance/activate   Activate via API"
            echo "  POST /system/maintenance/deactivate Deactivate via API"
            exit 1
            ;;
    esac
}

cmd_status() {
    ENVIRONMENT=""
    parse_env_args "$@"

    if [ -z "$ENVIRONMENT" ]; then
        detect_environment || die "No running Computor services detected. Specify an environment: $0 status dev|prod"
        log "Detected environment: ${YELLOW}$ENVIRONMENT${NC}"
    fi

    load_env
    derive_public_urls "$ENVIRONMENT"
    pin_project_name
    assemble_compose_files "$ENVIRONMENT"

    log "${BLUE}Services:${NC}"
    compose ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null \
        || echo "  Unable to query services"
    echo ""
    maintenance_status_report
}

cmd_update() {
    local action="${1:-status}"
    shift || true

    # Implemented in ops/lib/update.sh (self-update executor). Until that
    # lands, keep a stable CLI surface with explicit stubs.
    if [ -f "${OPS_DIR}/lib/update.sh" ]; then
        # shellcheck disable=SC1091
        source "${OPS_DIR}/lib/update.sh"
        dispatch_update "$action" "$@"
    else
        die "Self-update is not available in this checkout (ops/lib/update.sh missing)."
    fi
}

cmd_test() {
    # Backend pytest runner. Convenience flags map to pytest markers; anything
    # unrecognized passes through to pytest verbatim.
    local pytest_args=()
    while [[ $# -gt 0 ]]; do
        case $1 in
            --unit)         pytest_args+=(-m unit) ;;
            --integration)  pytest_args+=(-m integration) ;;
            --slow)         pytest_args+=(-m slow) ;;
            --file)
                [ -n "${2:-}" ] || die "--file requires a test file name"
                if [[ "$2" == *"test_"* ]]; then
                    pytest_args+=("computor_backend/tests/$2.py")
                else
                    pytest_args+=("$2")
                fi
                shift
                ;;
            -v|--verbose)   pytest_args+=(-vv) ;;
            -h|--help)      usage 0 ;;
            *)              pytest_args+=("$1") ;;
        esac
        shift
    done

    log "${GREEN}=== Computor Backend Tests ===${NC}"

    # Unit tests need no stack, so a missing .env is tolerated; with one, the
    # integration tests talk to the configured database instead of fallbacks.
    if [ -f "${REPO_ROOT}/.env" ]; then
        load_env && echo "  ✓ .env loaded"
    else
        warn "  No .env found — using default database settings."
    fi
    export POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
    export POSTGRES_PORT="${POSTGRES_PORT:-5432}"
    export POSTGRES_USER="${POSTGRES_USER:-postgres}"
    export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres_secret}"
    export POSTGRES_DB="${POSTGRES_DB:-computor}"
    log "  Database: ${YELLOW}${POSTGRES_USER}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}${NC}"

    [ -n "${VIRTUAL_ENV:-}" ] || warn "  No virtual environment active — using system Python."
    command -v pytest >/dev/null 2>&1 || die "pytest not found. Install the backend first:
  pip install -e ${REPO_ROOT}/computor-backend"

    cd "${REPO_ROOT}/computor-backend/src"
    log "\n${GREEN}Running pytest...${NC}"
    pytest "${pytest_args[@]}"
}

COMMAND="${1:-}"
shift || true

case "$COMMAND" in
    up)           cmd_up "$@" ;;
    down|stop)    cmd_down "$@" ;;
    status)       cmd_status "$@" ;;
    maintenance)  cmd_maintenance "$@" ;;
    update)       cmd_update "$@" ;;
    test)         cmd_test "$@" ;;
    -h|--help|help|"") usage 0 ;;
    *)
        log "${RED}Unknown command: $COMMAND${NC}"
        usage 1
        ;;
esac
