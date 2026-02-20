#!/bin/bash

# API startup script with configurable logging levels
# Default: Shows HTTP requests (uvicorn info) but quiet WebSocket logging

# Default values
WEBSOCKET_LOG_LEVEL="${WEBSOCKET_LOG_LEVEL:-WARNING}"  # Quiet WebSocket by default
UVICORN_LOG_LEVEL="${UVICORN_LOG_LEVEL:-info}"         # Show HTTP requests by default
RUN_MIGRATIONS=true

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-migrations)
            RUN_MIGRATIONS=false
            shift
            ;;
        --verbose|-v)
            export WEBSOCKET_LOG_LEVEL="INFO"
            export UVICORN_LOG_LEVEL="info"
            shift
            ;;
        --debug|-d)
            export WEBSOCKET_LOG_LEVEL="DEBUG"
            export UVICORN_LOG_LEVEL="debug"
            shift
            ;;
        --quiet|-q)
            export WEBSOCKET_LOG_LEVEL="ERROR"
            export UVICORN_LOG_LEVEL="error"  # This also hides HTTP requests
            shift
            ;;
        --help|-h)
            cat << EOF
Usage: $0 [OPTIONS]

Options:
  --no-migrations     Skip running Alembic migrations before starting
  --verbose, -v       Show WebSocket connection logs + HTTP requests
  --debug, -d         Show all debug logs (very verbose)
  --quiet, -q         Show only errors (hides HTTP requests too)
  --help, -h          Show this help message

Environment Variables:
  WEBSOCKET_LOG_LEVEL   Set WebSocket logging level (DEBUG, INFO, WARNING, ERROR)
  UVICORN_LOG_LEVEL     Set Uvicorn logging level (debug, info, warning, error)

Default: Runs migrations, shows HTTP requests, quiet WebSocket (no connection spam)

Examples:
  $0                           # Run migrations + start API (default)
  $0 --no-migrations           # Start API without running migrations
  $0 --verbose                 # Show WebSocket connections + HTTP requests
  $0 --debug                   # Show everything (very verbose)
  $0 --quiet                   # Only errors (no HTTP requests)

  WEBSOCKET_LOG_LEVEL=INFO $0  # Custom via environment
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

# Display startup information
echo "=========================================="
echo "Starting Computor Backend API"
echo "=========================================="
echo "WebSocket Log Level: $WEBSOCKET_LOG_LEVEL"
echo "Uvicorn Log Level: $UVICORN_LOG_LEVEL"
echo "Datetime Format: YYYY-MM-DD HH:MM:SS"

case $WEBSOCKET_LOG_LEVEL in
    DEBUG)
        echo "Mode: Debug (all messages shown)"
        ;;
    INFO)
        echo "Mode: Verbose (connections logged)"
        ;;
    WARNING)
        echo "Mode: Normal (HTTP requests shown, WebSocket quiet)"
        ;;
    ERROR)
        echo "Mode: Quiet (errors only, no HTTP requests)"
        ;;
esac

echo "=========================================="
echo ""

# Export for the Python server to use
export WEBSOCKET_LOG_LEVEL
export UVICORN_LOG_LEVEL

# Run migrations unless --no-migrations was passed
if [ "$RUN_MIGRATIONS" = true ]; then
    echo "Applying Alembic migrations..."
    cd computor-backend/src/computor_backend && alembic upgrade head && cd -  > /dev/null
    echo ""
fi

# Start the server
cd computor-backend/src && python3 server.py