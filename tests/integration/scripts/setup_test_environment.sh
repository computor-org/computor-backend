#!/bin/bash
# Integration Test Environment Setup Script
#
# This script helps set up the integration test environment by:
# 1. Checking for required services
# 2. Creating profile configuration
# 3. Deploying the test organization/course hierarchy
# 4. Verifying everything is ready

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$(cd "$SCRIPT_DIR/../config" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Integration Test Environment Setup"
echo "=========================================="
echo ""

# Check if .env file exists
if [ ! -f "$CONFIG_DIR/.env" ]; then
    echo -e "${RED}ERROR: .env file not found${NC}"
    echo "Please copy .env.template to .env and configure it:"
    echo ""
    echo "  cd $CONFIG_DIR"
    echo "  cp .env.template .env"
    echo "  # Edit .env with your GitLab server details"
    echo ""
    exit 1
fi

# Load environment variables
set -a
source "$CONFIG_DIR/.env"
set +a

echo -e "${GREEN}✓${NC} Configuration loaded from .env"

# Check if API is running
echo ""
echo "Checking Computor API..."
if curl -s -f "${API_BASE_URL}/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} API is running at ${API_BASE_URL}"
else
    echo -e "${RED}✗${NC} API is not responding at ${API_BASE_URL}"
    echo "Please start the API server first:"
    echo "  cd $ROOT_DIR"
    echo "  bash api.sh"
    exit 1
fi

# Check if GitLab is accessible
echo ""
echo "Checking GitLab server..."
if curl -s -f "${GITLAB_URL}" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} GitLab is accessible at ${GITLAB_URL}"
else
    echo -e "${YELLOW}⚠${NC} GitLab may not be accessible at ${GITLAB_URL}"
    echo "Continuing anyway..."
fi

# Create profile.yaml if it doesn't exist
PROFILE_FILE="$CONFIG_DIR/profile.yaml"
if [ ! -f "$PROFILE_FILE" ]; then
    echo ""
    echo "Creating profile configuration..."

    # Get admin credentials from .env
    ADMIN_USER="${ADMIN_USERNAME:-admin}"
    ADMIN_PASS="${ADMIN_PASSWORD:-admin123}"
    API_URL="${API_BASE_URL}"

    # Add /api suffix if not present
    if [[ ! "$API_URL" == */api ]]; then
        API_URL="${API_URL}/api"
    fi

    cat > "$PROFILE_FILE" << EOF
api_url: ${API_URL}
basic:
  username: ${ADMIN_USER}
  password: ${ADMIN_PASS}
EOF

    echo -e "${GREEN}✓${NC} Profile configuration created: $PROFILE_FILE"
else
    echo -e "${GREEN}✓${NC} Profile configuration exists: $PROFILE_FILE"
fi

# Check if computor CLI is available
if ! command -v computor &> /dev/null; then
    echo ""
    echo -e "${RED}✗${NC} computor CLI not found"
    echo "Please install it first:"
    echo "  cd $ROOT_DIR"
    echo "  pip install -e computor-cli/"
    exit 1
fi

# Deploy test hierarchy using computor CLI
echo ""
echo "=========================================="
echo "Deploying Test Hierarchy"
echo "=========================================="
echo ""
echo "Using deployment file: $CONFIG_DIR/deployment.yaml"
echo "Using profile: $PROFILE_FILE"
echo ""

# Deploy using the custom profile
echo "Deploying..."
if computor --profile "$PROFILE_FILE" deployment apply "$CONFIG_DIR/deployment.yaml"; then
    echo ""
    echo -e "${GREEN}✓${NC} Deployment successful"
else
    echo ""
    echo -e "${RED}✗${NC} Deployment failed"
    echo "Please check the error messages above"
    exit 1
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "You can now run the integration tests:"
echo ""
echo "  # Run all tests:"
echo "  cd $SCRIPT_DIR"
echo "  python3 run_all_tests.py"
echo ""
echo "  # Run individual test suites:"
echo "  python3 test_student_permissions.py"
echo "  python3 test_tutor_permissions.py"
echo "  python3 test_lecturer_permissions.py"
echo ""
