#!/bin/bash
set -e

###########################
# CLI PARAMETERS
###########################

CODER_DIR="/root/coder"
REMOVE_VOLUMES=false

# Parse command line arguments
while getopts "d:vh" opt; do
  case $opt in
    d)
      CODER_DIR="$OPTARG"
      ;;
    v)
      REMOVE_VOLUMES=true
      ;;
    h)
      echo "Usage: $0 [-d DIRECTORY] [-v]"
      echo ""
      echo "Options:"
      echo "  -d DIRECTORY  Coder installation directory (default: /root/coder)"
      echo "  -v            Remove volumes (destroys all data)"
      echo "  -h            Show this help"
      echo ""
      echo "Examples:"
      echo "  $0                    # Stop services, keep data"
      echo "  $0 -v                 # Stop and remove all data"
      echo "  $0 -d /opt/coder      # Stop services in custom directory"
      exit 0
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      echo "Use -h for help" >&2
      exit 1
      ;;
  esac
done

###########################
# AUTO-DETECT DIRECTORY
###########################

# If default directory doesn't have docker-compose.yml, check current directory
if [ "$CODER_DIR" = "/root/coder" ] && [ ! -f "${CODER_DIR}/docker-compose.yml" ]; then
  if [ -f "./docker-compose.yml" ]; then
    CODER_DIR="."
  fi
fi

###########################
# VALIDATION
###########################

if [ ! -f "${CODER_DIR}/docker-compose.yml" ]; then
  echo "ERROR: docker-compose.yml not found in ${CODER_DIR}"
  echo "Use -d to specify the Coder installation directory"
  exit 1
fi

###########################
# STOP SERVICES
###########################

cd "${CODER_DIR}"

if [ "$REMOVE_VOLUMES" = true ]; then
  echo "Stopping Coder and removing volumes..."
  docker compose down -v
  echo "All services stopped and volumes removed."
else
  echo "Stopping Coder..."
  docker compose down
  echo "All services stopped. Data volumes preserved."
fi

echo ""
echo "To restart: cd ${CODER_DIR} && docker compose up -d"
