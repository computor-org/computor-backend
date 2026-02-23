#!/bin/bash

# Web frontend (computor-web) development startup script
# Starts the Next.js dev server using yarn

set -e

PORT="${COMPUTOR_WEB_PORT:-3000}"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port|-p)
            PORT="$2"
            shift 2
            ;;
        --install|-i)
            INSTALL=true
            shift
            ;;
        --help|-h)
            cat << EOF
Usage: $0 [OPTIONS]

Options:
  --port, -p PORT   Set dev server port (default: 3000)
  --install, -i     Run yarn install before starting
  --help, -h        Show this help message

Environment Variables:
  NEXT_PUBLIC_API_URL    Backend API URL (default: http://localhost:8000)
  COMPUTOR_WEB_PORT      Dev server port (default: 3000)

Examples:
  $0                     # Start dev server on port 3000
  $0 --port 3001         # Start on custom port
  $0 --install           # Install deps + start
EOF
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Load environment variables from .env if it exists
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

cd computor-web

# Install dependencies if requested or if node_modules is missing
if [ "${INSTALL}" = true ] || [ ! -d node_modules ]; then
    echo "Installing dependencies..."
    yarn install
    echo ""
fi

echo "=========================================="
echo "Starting Computor Web (Next.js dev)"
echo "=========================================="
echo "URL: http://localhost:${PORT}"
echo "API: ${NEXT_PUBLIC_API_URL:-http://localhost:8000}"
echo "=========================================="
echo ""

PORT=$PORT yarn dev
