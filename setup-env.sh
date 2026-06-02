#!/bin/bash

# Environment setup script for Computor
# Creates .env.common - a template configuration file with all variables
# User should copy .env.common to .env and customize as needed
# startup.sh uses .env as the main configuration file

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Show help
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  --auto          Non-interactive mode with defaults"
    echo "  --force         Overwrite an existing .env.common without asking"
    echo "  --preserve      Don't create/copy .env, only (re)generate .env.common"
    echo "  --help, -h      Show this help message"
    echo ""
    echo "An existing .env is NEVER overwritten by this script."
    echo ""
    echo "Examples:"
    echo "  $0              Interactive setup (recommended for first time)"
    echo "  $0 --auto       Quick setup with defaults"
    echo "  $0 --preserve   Regenerate .env.common only; leave .env handling to you"
    echo "  $0 --force      Recreate .env.common (an existing .env is still kept)"
    exit 0
fi

echo -e "${GREEN}=== Computor Environment Setup ===${NC}"
echo -e "This script creates a unified environment configuration.\n"

# Check for existing .env file
if [ -f .env ]; then
    echo -e "${YELLOW}ℹ️  Existing .env detected — it will NOT be modified.${NC}"
    echo -e "Generated values go to .env.common; merge them into .env yourself.\n"
fi

# Function to generate secure random token
generate_token() {
    openssl rand -base64 32 2>/dev/null || cat /dev/urandom | head -c 32 | base64
}

# Function to generate secure hex token
generate_hex_token() {
    openssl rand -hex 32 2>/dev/null || cat /dev/urandom | head -c 32 | xxd -p -c 256
}

# Generate an API token in the backend's format: "ctp_" + 32 url-safe base64 chars.
# Mirrors computor_cli.api_token_cli.generate_api_token (secrets.token_urlsafe(24)[:32]).
# A deployment later registers this token's prefix + sha256 hash to create the
# matching service user, so the format must match exactly.
generate_api_token() {
    local rnd
    rnd=$(openssl rand -base64 24 2>/dev/null || cat /dev/urandom | head -c 24 | base64)
    rnd=$(printf '%s' "$rnd" | tr '+/' '-_' | tr -d '=\n\r' | cut -c1-32)
    printf 'ctp_%s' "$rnd"
}

# Function to prompt for value with default
prompt_value() {
    local prompt_text="$1"
    local default_value="$2"
    local secret_mode="$3"
    local value

    if [ -n "$default_value" ]; then
        prompt_text="$prompt_text [$default_value]"
    fi

    if [ "$secret_mode" = "true" ]; then
        read -r -s -p "$prompt_text: " value
        echo >&2  # Print newline to stderr for visual feedback
    else
        read -r -p "$prompt_text: " value
    fi

    if [ -z "$value" ]; then
        value="$default_value"
    fi

    # Remove any trailing newlines or carriage returns
    value=$(echo "$value" | tr -d '\n\r')

    echo "$value"
}

# Set KEY=value in $TARGET_FILE (OS-aware, anchored, | delimiter).
# Anchoring on ^KEY= avoids matching commented lines or longer keys that share
# a prefix (e.g. API_URL vs NEXT_PUBLIC_API_URL, KEYCLOAK_SERVER_URL vs ..._INTERNAL).
set_env_var() {
    local key="$1"
    local val="$2"
    # Escape characters that are special on the replacement side of sed s|||.
    local esc
    esc=$(printf '%s' "$val" | sed -e 's/[\\&|]/\\&/g')
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|^${key}=.*|${key}=${esc}|" "$TARGET_FILE"
    else
        sed -i "s|^${key}=.*|${key}=${esc}|" "$TARGET_FILE"
    fi
}

# Resolve an admin password: in interactive mode prompt (Enter = auto-generate);
# in --auto mode always auto-generate. The chosen value is echoed to stdout so
# the caller can both write it and report it in the final summary.
get_admin_password() {
    local label="$1"
    local pw
    if [ "$AUTO_MODE" = true ]; then
        generate_token | tr -d '/+=' | cut -c1-16
        return
    fi
    read -r -s -p "  ${label} (press Enter to auto-generate): " pw
    echo >&2  # newline to stderr so stdout stays clean for capture
    if [ -z "$pw" ]; then
        pw=$(generate_token | tr -d '/+=' | cut -c1-16)
    fi
    printf '%s' "$pw" | tr -d '\n\r'
}

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
OPS_DIR="${SCRIPT_DIR}/ops"

# Parse flags
FORCE_MODE=false
PRESERVE_EXISTING=false
AUTO_MODE=false

for arg in "$@"; do
    case $arg in
        --force)
            FORCE_MODE=true
            echo -e "${YELLOW}Force mode enabled - will overwrite existing files${NC}\n"
            ;;
        --preserve)
            PRESERVE_EXISTING=true
            echo -e "${YELLOW}Preserve mode - will keep existing .env${NC}\n"
            ;;
        --auto)
            AUTO_MODE=true
            echo -e "${YELLOW}Auto mode - using defaults${NC}\n"
            ;;
    esac
done

# Default values
ENVIRONMENT="dev"
DEPLOY_PATH="/opt/computor"  # host directory for all persistent data
ENABLE_CODER=false
ENABLE_FORGEJO=false
ENABLE_TESTING_WORKER=true  # --auto sets up a testing worker by default

# Interactive mode
if [ "$AUTO_MODE" != true ]; then
    echo -e "${BLUE}Interactive Setup Mode${NC}"
    echo "Press Enter to use default values, or type new values.\n"

    # Environment selection
    echo -e "${GREEN}1. Select environment:${NC}"
    PS3="Choose environment (1-2): "
    select ENV_TYPE in "Development" "Production"; do
        case $ENV_TYPE in
            Development)
                ENVIRONMENT="dev"
                break
                ;;
            Production)
                ENVIRONMENT="prod"
                break
                ;;
        esac
    done
    echo

    # Deployment path — host directory holding all persistent data and bind mounts.
    echo -e "${GREEN}2. Deployment path:${NC}"
    DEPLOY_PATH=$(prompt_value "Host directory for persistent data (DBs, MinIO, shared, documents)" "/opt/computor" false)
    echo

    # Git server setup (Keycloak is always enabled — it is the standard identity provider)
    echo -e "${GREEN}3. Git Server Integration:${NC}"
    read -p "Enable the Forgejo git server sidecar? (y/N): " enable_forgejo
    if [ "$enable_forgejo" = "y" ] || [ "$enable_forgejo" = "Y" ]; then
        ENABLE_FORGEJO=true
    fi
    echo

    # Testing worker setup — generates a pre-shared API token a deployment uses
    # to create the testing-worker service user.
    echo -e "${GREEN}4. Testing Worker:${NC}"
    read -p "Set up a testing worker (generate its API token)? (Y/n): " enable_tw
    if [ "$enable_tw" = "n" ] || [ "$enable_tw" = "N" ]; then
        ENABLE_TESTING_WORKER=false
    fi
    echo

    # Coder setup
    echo -e "${GREEN}5. Coder Integration:${NC}"
    read -p "Enable Coder workspace management? (y/N): " enable_coder
    if [ "$enable_coder" = "y" ] || [ "$enable_coder" = "Y" ]; then
        ENABLE_CODER=true
    fi
    echo
fi

# Create .env.common from template
echo -e "${GREEN}Creating unified environment configuration...${NC}"

TEMPLATE_FILE="${OPS_DIR}/environments/.env.common.template"
TARGET_FILE=".env.common"

# Check if should overwrite
if [ -f "$TARGET_FILE" ] && [ "$FORCE_MODE" != true ]; then
    echo -e "${YELLOW}File $TARGET_FILE already exists.${NC}"
    if [ "$AUTO_MODE" != true ]; then
        read -p "Overwrite? (y/N): " overwrite
        if [ "$overwrite" != "y" ] && [ "$overwrite" != "Y" ]; then
            echo "Keeping existing $TARGET_FILE"
            SKIP_COMMON=true
        fi
    else
        echo "Keeping existing $TARGET_FILE (auto mode)"
        SKIP_COMMON=true
    fi
fi

if [ "$SKIP_COMMON" != true ]; then
    if [ ! -f "$TEMPLATE_FILE" ]; then
        echo -e "${RED}Template $TEMPLATE_FILE not found!${NC}"
        exit 1
    fi

    echo -e "  Creating $TARGET_FILE from template..."
    cp "$TEMPLATE_FILE" "$TARGET_FILE"

    # Generate secure internal secrets (never typed by a human)
    echo -e "  Generating secure tokens..."

    TOKEN_SECRET=$(generate_token)
    AUTH_SECRET=$(generate_token)
    POSTGRES_PASSWORD=$(generate_token | tr -d '/+=' | cut -c1-20)
    REDIS_PASSWORD=$(generate_token | tr -d '/+=' | cut -c1-20)
    MINIO_PASSWORD=$(generate_token | tr -d '/+=' | cut -c1-20)
    TEMPORAL_PG_PASSWORD=$(generate_token | tr -d '/+=' | cut -c1-20)

    # Keycloak internal secrets. KEYCLOAK_CLIENT_SECRET must be hex: startup.sh
    # substitutes it into the realm config with a /-delimited sed, so it must
    # not contain '/'.
    KEYCLOAK_DB_PASSWORD=$(generate_token | tr -d '/+=' | cut -c1-20)
    KEYCLOAK_CLIENT_SECRET=$(generate_hex_token)
    # Forgejo's Keycloak OIDC client secret. Declared up-front in the realm import
    # (computor-realm.json) AND handed to Forgejo's login source, so both sides share
    # one fixed value — no runtime secret exchange. Hex for the same /-delimited sed
    # substitution reason as KEYCLOAK_CLIENT_SECRET.
    FORGEJO_KEYCLOAK_CLIENT_SECRET=$(generate_hex_token)

    set_env_var POSTGRES_PASSWORD "$POSTGRES_PASSWORD"
    set_env_var REDIS_PASSWORD "$REDIS_PASSWORD"
    set_env_var MINIO_ROOT_PASSWORD "$MINIO_PASSWORD"
    set_env_var TEMPORAL_POSTGRES_PASSWORD "$TEMPORAL_PG_PASSWORD"
    set_env_var TOKEN_SECRET "$TOKEN_SECRET"
    set_env_var AUTH_SECRET "$AUTH_SECRET"
    set_env_var KEYCLOAK_DB_PASSWORD "$KEYCLOAK_DB_PASSWORD"
    set_env_var KEYCLOAK_CLIENT_SECRET "$KEYCLOAK_CLIENT_SECRET"
    set_env_var FORGEJO_KEYCLOAK_CLIENT_SECRET "$FORGEJO_KEYCLOAK_CLIENT_SECRET"

    # Deployment path (host side). DOCUMENTS_ROOT follows it so the documents API
    # and the host volume stay aligned. API_ROOT_PATH is container-side and left at
    # its template default.
    set_env_var SYSTEM_DEPLOYMENT_PATH "$DEPLOY_PATH"
    set_env_var DOCUMENTS_ROOT "$DEPLOY_PATH/shared/documents"

    echo -e "  ${GREEN}✓${NC} Generated secure passwords and tokens"

    # Admin login passwords — prompt in interactive mode (Enter = auto-generate),
    # auto-generate in --auto mode. Reported in the summary at the end.
    if [ "$AUTO_MODE" != true ]; then
        echo -e "\n${BLUE}Admin credentials${NC} (press Enter to auto-generate a strong value):"
    fi
    API_ADMIN_PASSWORD=$(get_admin_password "Computor API admin password (login: admin@computor.local)")
    KEYCLOAK_ADMIN_PASSWORD=$(get_admin_password "Keycloak admin-console password (user: admin)")
    set_env_var API_ADMIN_PASSWORD "$API_ADMIN_PASSWORD"
    set_env_var KEYCLOAK_ADMIN_PASSWORD "$KEYCLOAK_ADMIN_PASSWORD"

    # Configure environment-specific settings
    echo -e "  Configuring for $ENVIRONMENT environment..."

    if [ "$ENVIRONMENT" = "dev" ]; then
        # Development settings
        set_env_var DEBUG_MODE development
        set_env_var DISABLE_API_DEBUG_INFO false
        set_env_var TEMPORAL_WORKER_REPLICAS 1
        set_env_var TESTING_WORKER_REPLICAS 1
        # API_URL: Docker workers reach the host-run backend. Mac and Linux differ.
        if [[ "$OSTYPE" == "darwin"* ]]; then
            set_env_var API_URL http://host.docker.internal:8000
        else
            set_env_var API_URL http://172.17.0.1:8000
        fi
        # Browser-facing API URL (web runs locally in dev).
        set_env_var NEXT_PUBLIC_API_URL http://localhost:8000
        # Backend reaches Coder on localhost; workspaces call back to the host.
        set_env_var CODER_URL http://localhost:7080
        set_env_var BACKEND_EXTERNAL_URL http://host.docker.internal:8000
    else
        # Production settings
        set_env_var DEBUG_MODE production
        set_env_var DISABLE_API_DEBUG_INFO true
        set_env_var TEMPORAL_WORKER_REPLICAS 2
        set_env_var TESTING_WORKER_REPLICAS 2
        # API_URL: backend runs as the 'uvicorn' container on computor-network.
        set_env_var API_URL http://uvicorn:8000
        # NEXT_PUBLIC_API_URL is baked into the web build and must be browser-reachable:
        # the public HTTPS domain with the /api path. Ask for the domain.
        if [ "$AUTO_MODE" = true ]; then
            PUBLIC_DOMAIN="https://yourdomain.com"
        else
            while true; do
                PUBLIC_DOMAIN=$(prompt_value "Public HTTPS domain for the web frontend (e.g. https://computor.example.com)" "https://yourdomain.com" false)
                PUBLIC_DOMAIN="${PUBLIC_DOMAIN%/}"  # strip trailing slash
                if [[ "$PUBLIC_DOMAIN" =~ ^https?:// ]]; then
                    break
                fi
                echo "  Invalid URL — must start with http:// or https:// (got: $PUBLIC_DOMAIN)" >&2
            done
        fi
        PUBLIC_DOMAIN="${PUBLIC_DOMAIN%/}"  # strip trailing slash so we don't get //api
        # Single source of truth for the public URLs. startup.sh derives
        # NEXT_PUBLIC_API_URL / KEYCLOAK_PUBLIC_URL / FORGEJO_ROOT_URL / FORGEJO_DOMAIN
        # from this at launch, so leave those empty here (a domain change is then a
        # one-line edit). Set any of them explicitly later to override its derivation.
        set_env_var PUBLIC_DOMAIN "$PUBLIC_DOMAIN"
        set_env_var NEXT_PUBLIC_API_URL ""
        # Keycloak: expose via Traefik at /auth; the public URL itself comes from PUBLIC_DOMAIN.
        set_env_var KEYCLOAK_TRAEFIK_ENABLED true
        set_env_var KEYCLOAK_HTTP_RELATIVE_PATH /auth
        set_env_var KEYCLOAK_PUBLIC_URL ""
        # Backend reaches Coder over computor-network; workspaces call back via Traefik.
        set_env_var CODER_URL http://coder:7080
        set_env_var BACKEND_EXTERNAL_URL http://localhost:8080/api
    fi

    # Configure the testing worker if requested. The token is pre-shared: a
    # deployment registers its prefix + hash to create the worker's service user.
    if [ "$ENABLE_TESTING_WORKER" = true ]; then
        echo -e "  Configuring testing worker..."
        TESTING_WORKER_TOKEN=$(generate_api_token)
        set_env_var TESTING_WORKER_TOKEN "$TESTING_WORKER_TOKEN"
        echo -e "  ${GREEN}✓${NC} Generated TESTING_WORKER_TOKEN"
    fi

    # Configure Forgejo git server if enabled
    if [ "$ENABLE_FORGEJO" = true ]; then
        echo -e "  Configuring Forgejo git server..."

        # Internal Forgejo Postgres credential — fail-closed in the compose file,
        # never typed by a human.
        FORGEJO_DB_PASSWORD=$(generate_token | tr -d '/+=' | cut -c1-20)

        # Admin login for the Forgejo web UI (prompt / auto-generate like the others).
        GIT_SERVER_ADMIN_PASSWORD=$(get_admin_password "Forgejo admin password (user: forgejo-admin)")

        set_env_var GIT_SERVER forgejo
        set_env_var FORGEJO_DB_PASSWORD "$FORGEJO_DB_PASSWORD"
        set_env_var GIT_SERVER_ADMIN_PASSWORD "$GIT_SERVER_ADMIN_PASSWORD"

        # Public exposure. Dev: direct port (localhost:3030), no Traefik. Prod: served
        # behind Traefik under the /forgejo subpath. FORGEJO_ROOT_URL and FORGEJO_DOMAIN
        # are derived from PUBLIC_DOMAIN by startup.sh, so leave them empty here (set
        # explicitly to override). startup.sh strips the scheme for FORGEJO_DOMAIN and
        # appends /forgejo for FORGEJO_ROOT_URL.
        if [ "$ENVIRONMENT" = "prod" ]; then
            set_env_var FORGEJO_TRAEFIK_ENABLED true
            set_env_var FORGEJO_DOMAIN ""
            set_env_var FORGEJO_ROOT_URL ""
        fi

        echo -e "  ${GREEN}✓${NC} Forgejo configuration complete"
    fi

    # Configure Coder if enabled. Coder's server is internal-only (bound to
    # 127.0.0.1, not behind Traefik — only workspaces are exposed via Traefik),
    # and all its credentials are backend-to-Coder-API, so everything here is
    # generated automatically with nothing to prompt for.
    if [ "$ENABLE_CODER" = true ]; then
        echo -e "  Configuring Coder integration..."

        # Internal credentials (all fail-closed / backend-only, never human-typed):
        #   CODER_POSTGRES_PASSWORD  — Coder's database
        #   CODER_ADMIN_PASSWORD     — backend's login to the Coder API
        #   CODER_ADMIN_API_SECRET   — openssl rand -hex 32, as computor-coder expects
        CODER_PG_PASSWORD=$(generate_token | tr -d '/+=' | cut -c1-20)
        CODER_ADMIN_PASSWORD=$(generate_token | tr -d '/+=' | cut -c1-16)
        CODER_API_SECRET=$(openssl rand -hex 32 2>/dev/null || generate_hex_token)

        # Coder's admin email always mirrors the platform admin email.
        CODER_ADMIN_EMAIL=$(grep -E '^API_ADMIN_EMAIL=' "$TARGET_FILE" | cut -d= -f2-)

        set_env_var CODER_ENABLED true
        set_env_var CODER_POSTGRES_PASSWORD "$CODER_PG_PASSWORD"
        set_env_var CODER_ADMIN_PASSWORD "$CODER_ADMIN_PASSWORD"
        set_env_var CODER_ADMIN_API_SECRET "$CODER_API_SECRET"
        set_env_var CODER_ADMIN_EMAIL "$CODER_ADMIN_EMAIL"

        echo -e "  ${GREEN}✓${NC} Coder configuration complete"
    fi

    echo -e "  ${GREEN}✓${NC} Created .env.common"
fi

# Make .env usable by startup.sh — but NEVER overwrite an existing .env.
# startup.sh reads .env only; .env.common is just the generated template.
ENV_READY=false
if [ -f .env ]; then
    # An existing .env is the source of truth — leave it untouched.
    echo -e "\n${YELLOW}Existing .env found — left untouched.${NC}"
    echo -e "  Generated values were written to .env.common only."
    echo -e "  Diff and merge any new variables yourself: ${BLUE}diff .env .env.common${NC}"
elif [ "$PRESERVE_EXISTING" = true ]; then
    echo -e "\n${YELLOW}--preserve: not creating .env. Copy it yourself when ready:${NC}"
    echo -e "  cp .env.common .env"
elif [ "$AUTO_MODE" = true ]; then
    cp .env.common .env
    ENV_READY=true
    echo -e "\n  ${GREEN}✓${NC} Copied .env.common to .env"
else
    read -r -p "Copy .env.common to .env now so you can start the stack? (Y/n): " do_copy
    if [ -z "$do_copy" ] || [ "$do_copy" = "y" ] || [ "$do_copy" = "Y" ]; then
        cp .env.common .env
        ENV_READY=true
        echo -e "  ${GREEN}✓${NC} Copied .env.common to .env"
    else
        echo -e "  ${YELLOW}Skipped. Copy it yourself when ready:${NC} cp .env.common .env"
    fi
fi

# Final summary
echo -e "\n${GREEN}=== Setup Complete ===${NC}"
echo -e "Created:"
[ -f .env.common ] && echo -e "  ${GREEN}✓${NC} .env.common - configuration template with ALL variables"
[ "$ENV_READY" = true ] && echo -e "  ${GREEN}✓${NC} .env - ready for ./startup.sh"

# Report the admin credentials (generated or entered) so the user can log in.
# Only populated when .env.common was (re)generated this run.
if [ -n "$API_ADMIN_PASSWORD" ]; then
    echo -e "\n${GREEN}Admin credentials${NC} (also stored in .env.common):"
    echo -e "  Computor API admin:  admin@computor.local / ${YELLOW}${API_ADMIN_PASSWORD}${NC}"
    echo -e "  Keycloak console:    admin / ${YELLOW}${KEYCLOAK_ADMIN_PASSWORD}${NC}"
    if [ "$ENABLE_FORGEJO" = true ]; then
        echo -e "  Forgejo admin:       forgejo-admin / ${YELLOW}${GIT_SERVER_ADMIN_PASSWORD}${NC}"
    fi
    # Coder admin credentials are intentionally omitted — they are internal
    # (backend-to-Coder API) and not meant for human login.
fi

# Show the testing-worker token so a deployment can register its service user.
if [ -n "$TESTING_WORKER_TOKEN" ]; then
    echo -e "\n${GREEN}Testing worker token${NC} (give this to your deployment to create the worker user):"
    echo -e "  TESTING_WORKER_TOKEN=${YELLOW}${TESTING_WORKER_TOKEN}${NC}"
fi

echo -e "\n${YELLOW}Important:${NC}"
echo "1. Review and edit .env.common as needed"
echo "2. Keep these files secure - they contain passwords"
echo "3. Never commit .env files to version control"

# External SSO is intentionally NOT prompted here: a brokered IdP's client secret
# is issued by the institute's provider (we don't generate it), and the provider
# list is operator-managed and local-only. Just point the way.
echo -e "\n${BLUE}Optional — external SSO (brokered through Keycloak):${NC}"
echo "  To let users sign in via an institute IdP (config stays local, not committed):"
echo "    1. cp data/keycloak/identity-providers.example.json data/keycloak/identity-providers.json"
echo "       then set alias / discoveryUrl / clientId and \"enabled\": true"
echo "    2. add its secret to .env:  IDP_<ALIAS>_CLIENT_SECRET=..."
echo "    3. ./startup.sh — the keycloak-idp-setup step registers it (idempotent)"

echo -e "\n${GREEN}To start Computor:${NC}"
echo "  ./startup.sh $ENVIRONMENT -d"
if [ "$ENABLE_CODER" = true ]; then
    echo "  (Coder is enabled via CODER_ENABLED=true in .env)"
fi

echo -e "\n${GREEN}To stop Computor:${NC}"
echo "  ./stop.sh $ENVIRONMENT"