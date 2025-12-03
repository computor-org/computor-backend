#!/bin/bash
# Unified code generation script for Computor
# Generates TypeScript types, clients, validators, schemas, and error codes

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

# shellcheck disable=SC1090
source "${ROOT_DIR}/scripts/utilities/ensure_venv.sh"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print usage
usage() {
    cat << EOF
Usage: bash generate.sh [OPTIONS] [TARGET]

Generate code artifacts for the Computor platform.

TARGETS:
    types           Generate TypeScript interfaces from Pydantic models
    clients         Generate TypeScript API client classes
    python-client   Generate Python HTTP client library
    validators      Generate TypeScript validation classes
    schema          Generate JSON Schema for meta.yaml files
    error-codes     Generate error code definitions (TypeScript, JSON, Markdown)
    all             Generate all artifacts (default)

OPTIONS:
    -h, --help      Show this help message
    -w, --watch     Watch mode for types generation
    --no-error-codes Skip error codes generation when using 'types' or 'all'

EXAMPLES:
    bash generate.sh                    # Generate all artifacts
    bash generate.sh types              # Generate only TypeScript types
    bash generate.sh types --watch      # Generate types in watch mode
    bash generate.sh clients validators # Generate clients and validators
    bash generate.sh all --no-error-codes  # Generate all except error codes

EOF
    exit 0
}

# Parse arguments
TARGETS=()
WATCH_MODE=false
SKIP_ERROR_CODES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            ;;
        -w|--watch)
            WATCH_MODE=true
            shift
            ;;
        --no-error-codes)
            SKIP_ERROR_CODES=true
            shift
            ;;
        *)
            TARGETS+=("$1")
            shift
            ;;
    esac
done

# Default to 'all' if no targets specified
if [ ${#TARGETS[@]} -eq 0 ]; then
    TARGETS=("all")
fi

# Ensure virtual environment
ensure_venv

# Determine Python binary
PYTHON_BIN="${PYTHON_BIN:-python}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    PYTHON_BIN="python3"
fi

# Set PYTHONPATH
export PYTHONPATH="${ROOT_DIR}/computor-backend/src:${ROOT_DIR}/computor-types/src:${ROOT_DIR}/computor-cli/src${PYTHONPATH:+:${PYTHONPATH}}"

# Function to generate TypeScript types
generate_types() {
    echo -e "${BLUE}🚀 Generating TypeScript interfaces from Pydantic models...${NC}"

    local args=()
    if [ "$WATCH_MODE" = true ]; then
        args+=("--watch")
    fi

    cd "${ROOT_DIR}" && \
        "${PYTHON_BIN}" "${ROOT_DIR}/computor-backend/src/computor_backend/scripts/generate_typescript_interfaces.py" ${args[@]+"${args[@]}"}

    echo -e "${GREEN}✅ TypeScript interfaces generated successfully!${NC}"
    echo -e "📁 Check frontend/src/types/generated/ for the generated files\n"
}

# Function to generate TypeScript clients
generate_clients() {
    echo -e "${BLUE}🛠️  Generating TypeScript API clients...${NC}"

    cd "${ROOT_DIR}" && \
        "${PYTHON_BIN}" "${ROOT_DIR}/computor-backend/src/computor_backend/scripts/generate_typescript_clients.py" "$@"

    echo -e "${GREEN}✅ TypeScript API clients generated successfully!${NC}"
    echo -e "📁 Check frontend/src/api/generated/ for the generated files\n"
}

# Function to generate Python client
generate_python_client() {
    echo -e "${BLUE}🐍 Generating Python HTTP client library...${NC}"

    cd "${ROOT_DIR}" && \
        "${PYTHON_BIN}" "${ROOT_DIR}/computor-backend/src/computor_backend/scripts/generate_python_clients.py" "$@"

    echo -e "${GREEN}✅ Python client library generated successfully!${NC}"
    echo -e "📁 Check computor-client/src/computor_client/ for the generated files\n"
}

# Function to generate TypeScript validators
generate_validators() {
    echo -e "${BLUE}🚀 Generating TypeScript Validation Classes...${NC}"

    cd "${ROOT_DIR}" && \
        "${PYTHON_BIN}" "${ROOT_DIR}/computor-backend/src/computor_backend/scripts/generate_typescript_validators.py" --export-schemas "$@"

    echo -e "${GREEN}✅ Validation classes generated successfully!${NC}"
    echo -e "📁 Schemas: frontend/src/types/schemas/"
    echo -e "📁 Validators: frontend/src/types/validators/\n"
}

# Function to generate JSON schema
generate_schema() {
    echo -e "${BLUE}🔧 Generating JSON Schema for meta.yaml files...${NC}"

    cd "${ROOT_DIR}" && \
        "${PYTHON_BIN}" "${ROOT_DIR}/computor-backend/src/computor_backend/scripts/generate_pydantic_schemas.py" "$@"

    echo -e "${GREEN}✅ JSON Schema generation completed successfully!${NC}\n"
}

# Function to generate error codes
generate_error_codes() {
    if [ "$SKIP_ERROR_CODES" = true ]; then
        echo -e "${YELLOW}⏭️  Skipping error code generation (--no-error-codes flag)${NC}\n"
        return
    fi

    echo -e "${BLUE}🚨 Generating error code definitions...${NC}"

    # Check if error_registry.yaml exists
    if [ ! -f "${ROOT_DIR}/computor-backend/error_registry.yaml" ]; then
        echo -e "${YELLOW}⚠️  Warning: error_registry.yaml not found in computor-backend/. Skipping error codes.${NC}\n"
        return
    fi

    # Check if PyYAML is installed
    if ! "${PYTHON_BIN}" -c "import yaml" 2>/dev/null; then
        echo "Installing PyYAML..."
        pip install pyyaml
    fi

    cd "${ROOT_DIR}" && \
        "${PYTHON_BIN}" "${ROOT_DIR}/computor-backend/src/computor_backend/scripts/generate_error_codes.py"

    echo -e "${GREEN}✅ Error code definitions generated successfully!${NC}\n"
}

# Main generation logic
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Computor Code Generation Tool       ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}\n"

for target in "${TARGETS[@]}"; do
    case $target in
        types)
            generate_types
            if [ "$SKIP_ERROR_CODES" = false ]; then
                generate_error_codes
            fi
            ;;
        clients)
            generate_clients
            ;;
        python-client)
            generate_python_client
            ;;
        validators)
            generate_validators
            ;;
        schema)
            generate_schema
            ;;
        error-codes)
            generate_error_codes
            ;;
        all)
            generate_types
            generate_clients
            generate_python_client
            generate_validators
            generate_schema
            if [ "$SKIP_ERROR_CODES" = false ]; then
                generate_error_codes
            fi
            ;;
        *)
            echo -e "${YELLOW}⚠️  Unknown target: $target${NC}"
            echo "Run 'bash generate.sh --help' for usage information"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Generation Complete! ✨              ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
