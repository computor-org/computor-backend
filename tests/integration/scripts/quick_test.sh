#!/bin/bash
# Quick Integration Test Script
#
# Runs a single test suite or all tests quickly without full setup

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="$(cd "$SCRIPT_DIR/../config" && pwd)"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Load environment
if [ -f "$CONFIG_DIR/.env" ]; then
    set -a
    source "$CONFIG_DIR/.env"
    set +a
else
    echo -e "${YELLOW}Warning: .env file not found, using defaults${NC}"
fi

# Parse command line arguments
TEST_SUITE="${1:-all}"

echo "=========================================="
echo "Quick Integration Test"
echo "=========================================="
echo ""

case "$TEST_SUITE" in
    student|students)
        echo "Running: Student Permission Tests"
        python3 "$SCRIPT_DIR/test_student_permissions.py"
        ;;
    tutor|tutors)
        echo "Running: Tutor Permission Tests"
        python3 "$SCRIPT_DIR/test_tutor_permissions.py"
        ;;
    lecturer|lecturers)
        echo "Running: Lecturer Permission Tests"
        python3 "$SCRIPT_DIR/test_lecturer_permissions.py"
        ;;
    all)
        echo "Running: All Permission Tests"
        python3 "$SCRIPT_DIR/run_all_tests.py"
        ;;
    *)
        echo "Usage: $0 [student|tutor|lecturer|all]"
        echo ""
        echo "Examples:"
        echo "  $0 student    # Run student tests only"
        echo "  $0 tutor      # Run tutor tests only"
        echo "  $0 lecturer   # Run lecturer tests only"
        echo "  $0 all        # Run all tests (default)"
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}Test execution complete!${NC}"
