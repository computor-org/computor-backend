#!/bin/bash

# Test runner script for Computor backend

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}🧪 Computor Backend Test Runner${NC}"
echo "=================================="

# Change to src directory
cd computor-backend/src

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo -e "${YELLOW}⚠️  Virtual environment not activated${NC}"
    echo "Please activate your virtual environment first:"
    echo "  python3 -m venv .venv"
    echo "  source .venv/bin/activate"
    echo ""
    echo "Or if you have an existing virtual environment, activate it."
    # Continue anyway - maybe pytest is installed globally
fi

# Set environment variables
export POSTGRES_HOST=${POSTGRES_HOST:-localhost}
export POSTGRES_PORT=${POSTGRES_PORT:-5432}
export POSTGRES_USER=${POSTGRES_USER:-postgres}
export POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres_secret}
export POSTGRES_DB=${POSTGRES_DB:-computor}

echo -e "${GREEN}📋 Environment:${NC}"
echo "  POSTGRES_HOST: $POSTGRES_HOST"
echo "  POSTGRES_USER: $POSTGRES_USER"
echo "  POSTGRES_DB: $POSTGRES_DB"
echo ""

# Parse command line arguments
PYTEST_ARGS=""
RUN_ALL=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            PYTEST_ARGS="$PYTEST_ARGS -m unit"
            RUN_ALL=false
            shift
            ;;
        --integration)
            PYTEST_ARGS="$PYTEST_ARGS -m integration"
            RUN_ALL=false
            shift
            ;;
        --slow)
            PYTEST_ARGS="$PYTEST_ARGS -m slow"
            RUN_ALL=false
            shift
            ;;
        --file)
            # Add the test file with proper path
            if [[ "$2" == *"test_"* ]]; then
                PYTEST_ARGS="$PYTEST_ARGS computor_backend/tests/$2.py"
            else
                PYTEST_ARGS="$PYTEST_ARGS $2"
            fi
            RUN_ALL=false
            shift 2
            ;;
        --verbose|-v)
            PYTEST_ARGS="$PYTEST_ARGS -vv"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --unit           Run only unit tests (no database required)"
            echo "  --integration    Run only integration tests (database required)"
            echo "  --slow           Run only slow tests"
            echo "  --file <file>    Run specific test file"
            echo "  --verbose, -v    Verbose output"
            echo "  --help, -h       Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                     # Run all tests"
            echo "  $0 --unit              # Run only unit tests"
            echo "  $0 --file test_models  # Run specific test file"
            echo "  $0 -v --integration    # Run integration tests with verbose output"
            exit 0
            ;;
        *)
            PYTEST_ARGS="$PYTEST_ARGS $1"
            shift
            ;;
    esac
done

# Run pytest
echo -e "${GREEN}🚀 Running tests...${NC}"
echo ""

if command -v pytest &> /dev/null; then
    pytest $PYTEST_ARGS
    TEST_EXIT_CODE=$?
else
    echo -e "${RED}❌ pytest not found!${NC}"
    echo "Please install test dependencies:"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Show test results
echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
else
    echo -e "${RED}❌ Some tests failed${NC}"
    exit $TEST_EXIT_CODE
fi