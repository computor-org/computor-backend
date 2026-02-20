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
    echo "  --force         Overwrite existing files without asking"
    echo "  --preserve      Keep existing .env if present"
    echo "  --help, -h      Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0              Interactive setup (recommended for first time)"
    echo "  $0 --auto       Quick setup with defaults"
    echo "  $0 --preserve   Keep existing .env, only update .env.common"
    echo "  $0 --force      Recreate all files (careful!)"
    exit 0
fi

echo -e "${GREEN}=== Computor Environment Setup ===${NC}"
echo -e "This script creates a unified environment configuration.\n"

# Check for existing .env file
if [ -f .env ] && [ "$1" != "--force" ]; then
    echo -e "${YELLOW}⚠️  Warning: Existing .env file detected!${NC}"
    echo -e "This file will be backed up and replaced."
    echo -e "Your existing configuration will be preserved in a backup file.\n"
fi

# Function to generate secure random token
generate_token() {
    openssl rand -base64 32 2>/dev/null || cat /dev/urandom | head -c 32 | base64
}

# Function to generate secure hex token
generate_hex_token() {
    openssl rand -hex 32 2>/dev/null || cat /dev/urandom | head -c 32 | xxd -p -c 256
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
ENABLE_CODER=false

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

    # Coder setup
    echo -e "${GREEN}2. Coder Integration:${NC}"
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

    # Generate secure tokens
    echo -e "  Generating secure tokens..."

    TOKEN_SECRET=$(generate_token)
    AUTH_SECRET=$(generate_token)
    POSTGRES_PASSWORD=$(generate_token | tr -d '/+=' | cut -c1-20)
    REDIS_PASSWORD=$(generate_token | tr -d '/+=' | cut -c1-20)
    MINIO_PASSWORD=$(generate_token | tr -d '/+=' | cut -c1-20)
    ADMIN_PASSWORD=$(generate_token | tr -d '/+=' | cut -c1-16)
    TESTING_WORKER_TOKEN=$(generate_hex_token | cut -c1-32)
    MATLAB_WORKER_TOKEN=$(generate_hex_token | cut -c1-32)

    # Update tokens in .env.common using | as delimiter to avoid conflicts with special characters
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$POSTGRES_PASSWORD|" "$TARGET_FILE"
        sed -i '' "s|REDIS_PASSWORD=.*|REDIS_PASSWORD=$REDIS_PASSWORD|" "$TARGET_FILE"
        sed -i '' "s|MINIO_ROOT_PASSWORD=.*|MINIO_ROOT_PASSWORD=$MINIO_PASSWORD|" "$TARGET_FILE"
        sed -i '' "s|TOKEN_SECRET=.*|TOKEN_SECRET=$TOKEN_SECRET|" "$TARGET_FILE"
        sed -i '' "s|AUTH_SECRET=.*|AUTH_SECRET=$AUTH_SECRET|" "$TARGET_FILE"
        sed -i '' "s|API_ADMIN_PASSWORD=.*|API_ADMIN_PASSWORD=$ADMIN_PASSWORD|" "$TARGET_FILE"
        sed -i '' "s|TESTING_WORKER_TOKEN=.*|TESTING_WORKER_TOKEN=$TESTING_WORKER_TOKEN|" "$TARGET_FILE"
        sed -i '' "s|MATLAB_WORKER_TOKEN=.*|MATLAB_WORKER_TOKEN=$MATLAB_WORKER_TOKEN|" "$TARGET_FILE"
    else
        # Linux
        sed -i "s|POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$POSTGRES_PASSWORD|" "$TARGET_FILE"
        sed -i "s|REDIS_PASSWORD=.*|REDIS_PASSWORD=$REDIS_PASSWORD|" "$TARGET_FILE"
        sed -i "s|MINIO_ROOT_PASSWORD=.*|MINIO_ROOT_PASSWORD=$MINIO_PASSWORD|" "$TARGET_FILE"
        sed -i "s|TOKEN_SECRET=.*|TOKEN_SECRET=$TOKEN_SECRET|" "$TARGET_FILE"
        sed -i "s|AUTH_SECRET=.*|AUTH_SECRET=$AUTH_SECRET|" "$TARGET_FILE"
        sed -i "s|API_ADMIN_PASSWORD=.*|API_ADMIN_PASSWORD=$ADMIN_PASSWORD|" "$TARGET_FILE"
        sed -i "s|TESTING_WORKER_TOKEN=.*|TESTING_WORKER_TOKEN=$TESTING_WORKER_TOKEN|" "$TARGET_FILE"
        sed -i "s|MATLAB_WORKER_TOKEN=.*|MATLAB_WORKER_TOKEN=$MATLAB_WORKER_TOKEN|" "$TARGET_FILE"
    fi

    echo -e "  ${GREEN}✓${NC} Generated secure passwords and tokens"

    # Configure environment-specific settings
    echo -e "  Configuring for $ENVIRONMENT environment..."

    if [ "$ENVIRONMENT" = "dev" ]; then
        # Development settings
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|DEBUG_MODE=.*|DEBUG_MODE=development|" "$TARGET_FILE"
            sed -i '' "s|DISABLE_API_DEBUG_INFO=.*|DISABLE_API_DEBUG_INFO=false|" "$TARGET_FILE"
            sed -i '' "s|TEMPORAL_WORKER_REPLICAS=.*|TEMPORAL_WORKER_REPLICAS=1|" "$TARGET_FILE"
            sed -i '' "s|TESTING_WORKER_REPLICAS=.*|TESTING_WORKER_REPLICAS=1|" "$TARGET_FILE"
        else
            sed -i "s|DEBUG_MODE=.*|DEBUG_MODE=development|" "$TARGET_FILE"
            sed -i "s|DISABLE_API_DEBUG_INFO=.*|DISABLE_API_DEBUG_INFO=false|" "$TARGET_FILE"
            sed -i "s|TEMPORAL_WORKER_REPLICAS=.*|TEMPORAL_WORKER_REPLICAS=1|" "$TARGET_FILE"
            sed -i "s|TESTING_WORKER_REPLICAS=.*|TESTING_WORKER_REPLICAS=1|" "$TARGET_FILE"
        fi
    else
        # Production settings
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|DEBUG_MODE=.*|DEBUG_MODE=production|" "$TARGET_FILE"
            sed -i '' "s|DISABLE_API_DEBUG_INFO=.*|DISABLE_API_DEBUG_INFO=true|" "$TARGET_FILE"
            sed -i '' "s|TEMPORAL_WORKER_REPLICAS=.*|TEMPORAL_WORKER_REPLICAS=2|" "$TARGET_FILE"
            sed -i '' "s|TESTING_WORKER_REPLICAS=.*|TESTING_WORKER_REPLICAS=2|" "$TARGET_FILE"
            sed -i '' "s|API_URL=.*|API_URL=https://api.yourdomain.com|" "$TARGET_FILE"
            sed -i '' "s|NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=https://api.yourdomain.com|" "$TARGET_FILE"
        else
            sed -i "s|DEBUG_MODE=.*|DEBUG_MODE=production|" "$TARGET_FILE"
            sed -i "s|DISABLE_API_DEBUG_INFO=.*|DISABLE_API_DEBUG_INFO=true|" "$TARGET_FILE"
            sed -i "s|TEMPORAL_WORKER_REPLICAS=.*|TEMPORAL_WORKER_REPLICAS=2|" "$TARGET_FILE"
            sed -i "s|TESTING_WORKER_REPLICAS=.*|TESTING_WORKER_REPLICAS=2|" "$TARGET_FILE"
            sed -i "s|API_URL=.*|API_URL=https://api.yourdomain.com|" "$TARGET_FILE"
            sed -i "s|NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=https://api.yourdomain.com|" "$TARGET_FILE"
        fi
    fi

    # Configure Coder if enabled
    if [ "$ENABLE_CODER" = true ]; then
        echo -e "  Configuring Coder integration..."

        # Enable Coder
        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|CODER_ENABLED=.*|CODER_ENABLED=true|" "$TARGET_FILE"
        else
            sed -i "s|CODER_ENABLED=.*|CODER_ENABLED=true|" "$TARGET_FILE"
        fi

        # Interactive Coder configuration
        if [ "$AUTO_MODE" != true ]; then
            echo -e "\n${BLUE}Coder Configuration:${NC}"

            CODER_DOMAIN=$(prompt_value "Coder domain (e.g., coder.example.com)" "coder.localhost" false)
            CODER_ADMIN_EMAIL=$(prompt_value "Coder admin email" "admin@example.com" false)
            CODER_ADMIN_PASSWORD=$(prompt_value "Coder admin password" "" true)

            if [ -z "$CODER_ADMIN_PASSWORD" ]; then
                CODER_ADMIN_PASSWORD=$(generate_token | tr -d '/+=' | cut -c1-16)
                echo -e "  Generated password: ${YELLOW}$CODER_ADMIN_PASSWORD${NC}"
            fi

            # Generate CODER_ADMIN_API_SECRET using same method as computor-coder/deployment/generate-secret.sh
            CODER_API_SECRET=$(openssl rand -hex 32 2>/dev/null || generate_hex_token)

            # Escape any pipe characters in user input for sed
            CODER_DOMAIN_ESCAPED=$(echo "$CODER_DOMAIN" | sed 's/|/\\|/g')
            CODER_ADMIN_EMAIL_ESCAPED=$(echo "$CODER_ADMIN_EMAIL" | sed 's/|/\\|/g')
            CODER_ADMIN_PASSWORD_ESCAPED=$(echo "$CODER_ADMIN_PASSWORD" | sed 's/|/\\|/g')

            # Update Coder configuration using | delimiter
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s|CODER_DOMAIN=.*|CODER_DOMAIN=$CODER_DOMAIN_ESCAPED|" "$TARGET_FILE"
                sed -i '' "s|CODER_ADMIN_EMAIL=.*|CODER_ADMIN_EMAIL=$CODER_ADMIN_EMAIL_ESCAPED|" "$TARGET_FILE"
                sed -i '' "s|CODER_ADMIN_PASSWORD=.*|CODER_ADMIN_PASSWORD=$CODER_ADMIN_PASSWORD_ESCAPED|" "$TARGET_FILE"
                sed -i '' "s|CODER_ADMIN_API_SECRET=.*|CODER_ADMIN_API_SECRET=$CODER_API_SECRET|" "$TARGET_FILE"
            else
                sed -i "s|CODER_DOMAIN=.*|CODER_DOMAIN=$CODER_DOMAIN_ESCAPED|" "$TARGET_FILE"
                sed -i "s|CODER_ADMIN_EMAIL=.*|CODER_ADMIN_EMAIL=$CODER_ADMIN_EMAIL_ESCAPED|" "$TARGET_FILE"
                sed -i "s|CODER_ADMIN_PASSWORD=.*|CODER_ADMIN_PASSWORD=$CODER_ADMIN_PASSWORD_ESCAPED|" "$TARGET_FILE"
                sed -i "s|CODER_ADMIN_API_SECRET=.*|CODER_ADMIN_API_SECRET=$CODER_API_SECRET|" "$TARGET_FILE"
            fi
        else
            # Auto mode - generate Coder credentials
            CODER_ADMIN_PASSWORD=$(generate_token | tr -d '/+=' | cut -c1-16)
            # Use same method as computor-coder/deployment/generate-secret.sh
            CODER_API_SECRET=$(openssl rand -hex 32 2>/dev/null || generate_hex_token)

            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s|CODER_ADMIN_PASSWORD=.*|CODER_ADMIN_PASSWORD=$CODER_ADMIN_PASSWORD|" "$TARGET_FILE"
                sed -i '' "s|CODER_ADMIN_API_SECRET=.*|CODER_ADMIN_API_SECRET=$CODER_API_SECRET|" "$TARGET_FILE"
            else
                sed -i "s|CODER_ADMIN_PASSWORD=.*|CODER_ADMIN_PASSWORD=$CODER_ADMIN_PASSWORD|" "$TARGET_FILE"
                sed -i "s|CODER_ADMIN_API_SECRET=.*|CODER_ADMIN_API_SECRET=$CODER_API_SECRET|" "$TARGET_FILE"
            fi
        fi

        echo -e "  ${GREEN}✓${NC} Coder configuration complete"
    fi

    echo -e "  ${GREEN}✓${NC} Created .env.common"
fi

# Note about .env file usage
if [ -f .env ]; then
    echo -e "\n${YELLOW}Note: Existing .env file found and preserved${NC}"
    echo -e "  New configuration template saved to .env.common"
    echo -e "  You may want to compare and update your .env with new variables from .env.common"
else
    echo -e "\n${YELLOW}Important: To use the configuration, copy .env.common to .env:${NC}"
    echo -e "  cp .env.common .env"
fi

# No longer creating environment-specific override files
# Everything should be in .env only

# Final summary
echo -e "\n${GREEN}=== Setup Complete ===${NC}"
echo -e "Created the following file:"
[ -f .env.common ] && echo -e "  ${GREEN}✓${NC} .env.common - Configuration template with ALL variables"

if [ ! -f .env ]; then
    echo -e "\n${YELLOW}Next step: Copy .env.common to .env${NC}"
    echo -e "  cp .env.common .env"
    echo -e "  Then edit .env with your specific configuration"
fi

if [ "$ENABLE_CODER" = true ]; then
    echo -e "\n${GREEN}Coder is ENABLED${NC}"
    echo -e "  Domain: ${CODER_DOMAIN:-coder.localhost}"
    echo -e "  Admin: ${CODER_ADMIN_EMAIL:-admin@example.com}"
    if [ -n "$CODER_ADMIN_PASSWORD" ]; then
        echo -e "  Password: ${YELLOW}$CODER_ADMIN_PASSWORD${NC}"
    fi
fi

echo -e "\n${YELLOW}Important:${NC}"
echo "1. Review and edit .env.common as needed"
echo "2. Keep these files secure - they contain passwords"
echo "3. Never commit .env files to version control"

echo -e "\n${GREEN}To start Computor:${NC}"
echo "  ./startup.sh $ENVIRONMENT -d"
if [ "$ENABLE_CODER" = true ]; then
    echo "  (Coder is enabled via CODER_ENABLED=true in .env)"
fi

echo -e "\n${GREEN}To stop Computor:${NC}"
echo "  ./stop.sh $ENVIRONMENT"