#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

###########################
# LOAD CONFIGURATION
###########################

# Load from .env if it exists (user-configured values)
if [ -f "${SCRIPT_DIR}/.env" ]; then
  set -a
  source "${SCRIPT_DIR}/.env"
  set +a
fi

# USE_HTTP is only a CLI flag, not in .env
USE_HTTP=${USE_HTTP:-false}

# Parse command line arguments (override .env values)
while getopts "d:p:Q:P:D:Hu:e:w:h" opt; do
  case $opt in
    d)
      CODER_DIR="$OPTARG"
      ;;
    p)
      CODER_POSTGRES_PASSWORD="$OPTARG"
      ;;
    Q)
      CODER_POSTGRES_PORT="$OPTARG"
      ;;
    P)
      CODER_PORT="$OPTARG"
      ;;
    D)
      CODER_DOMAIN="$OPTARG"
      ;;
    H)
      USE_HTTP=true
      ;;
    u)
      CODER_ADMIN_USERNAME="$OPTARG"
      ;;
    e)
      CODER_ADMIN_EMAIL="$OPTARG"
      ;;
    w)
      CODER_ADMIN_PASSWORD="$OPTARG"
      ;;
    h)
      echo "Usage: $0 [-d DIRECTORY] [-p PASSWORD] [-Q PGPORT] [-P PORT] [-D DOMAIN] [-H] [-u USER] [-e EMAIL] [-w PASS]"
      echo ""
      echo "Configuration: Copy .env.example to .env and edit values, or use CLI flags."
      echo "CLI flags override .env values."
      echo ""
      echo "Options:"
      echo "  -d DIRECTORY  Coder installation directory"
      echo "  -p PASSWORD   PostgreSQL password (auto-generated if empty)"
      echo "  -Q PGPORT     PostgreSQL host port"
      echo "  -P PORT       Coder port"
      echo "  -D DOMAIN     Coder domain"
      echo "  -H            Use HTTP instead of HTTPS"
      echo "  -u USERNAME   Admin username (optional)"
      echo "  -e EMAIL      Admin email (optional)"
      echo "  -w PASSWORD   Admin password (optional)"
      echo "  -h            Show this help"
      echo ""
      echo "Examples:"
      echo "  cp .env.example .env && vim .env && $0"
      echo "  $0 -D example.com -P 8443"
      echo "  $0 -D localhost -P 8443 -H"
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
# VALIDATION
###########################

if ! command -v docker &> /dev/null; then
  echo "ERROR: Docker is not installed or not in PATH"
  exit 1
fi

if ! docker info &> /dev/null; then
  echo "ERROR: Docker daemon is not running"
  exit 1
fi

if ! docker compose version &> /dev/null; then
  echo "ERROR: Docker Compose is not available"
  exit 1
fi

###########################
# GENERATE SECRETS
###########################

# Generate PostgreSQL password if not provided
if [ -z "$CODER_POSTGRES_PASSWORD" ]; then
  CODER_POSTGRES_PASSWORD=$(openssl rand -hex 16)
  echo "Generated PostgreSQL password."
fi

###########################
# USER INPUT (if not provided via flags)
###########################

if [ -z "$CODER_DOMAIN" ]; then
  read -p "Enter domain (e.g. computor.at): " CODER_DOMAIN
fi
echo "Domain set to: $CODER_DOMAIN"

if [ -z "$CODER_ACCESS_URL" ]; then
  if [ "$USE_HTTP" = true ]; then
    CODER_ACCESS_URL="http://${CODER_DOMAIN}"
  else
    CODER_ACCESS_URL="https://${CODER_DOMAIN}"
  fi
fi
echo "Coder Access URL set to: $CODER_ACCESS_URL"

if [ -z "$CODER_PORT" ]; then
  read -p "Enter port for Coder (e.g. 8443): " CODER_PORT
fi
echo "Port set to: $CODER_PORT"

###########################
# GENERATE ADMIN API SECRET
###########################

if [ -z "$CODER_ADMIN_API_SECRET" ]; then
  echo "Generating Admin API Secret for workspace creation protection..."
  CODER_ADMIN_API_SECRET=$(openssl rand -hex 32)
  echo "Admin API Secret generated."
fi

###########################
# ADMIN USER INPUT (if partial info provided)
###########################

if [ -n "$CODER_ADMIN_USERNAME" ] || [ -n "$CODER_ADMIN_EMAIL" ] || [ -n "$CODER_ADMIN_PASSWORD" ]; then
  echo ""
  echo "Admin user creation enabled."

  if [ -z "$CODER_ADMIN_USERNAME" ]; then
    read -p "Enter admin username: " CODER_ADMIN_USERNAME
  fi

  if [ -z "$CODER_ADMIN_EMAIL" ]; then
    read -p "Enter admin email: " CODER_ADMIN_EMAIL
  fi

  if [ -z "$CODER_ADMIN_PASSWORD" ]; then
    read -sp "Enter admin password: " CODER_ADMIN_PASSWORD
    echo ""
  fi
fi

###########################
# GET DOCKER GID
###########################

echo "Getting Docker Group ID for permissions..."
DOCKER_GID=$(getent group docker | cut -d: -f3)

if [ -z "$DOCKER_GID" ]; then
  echo "WARNING: Could not find Docker group. Using fallback 999."
  DOCKER_GID="999"
else
  echo "Docker Group ID found: $DOCKER_GID"
fi

###########################
# CREATE DIRECTORIES
###########################

echo "Creating Coder directory: $CODER_DIR"
mkdir -p "${CODER_DIR}"

###########################
# COPY TEMPLATE FILES
###########################

TEMPLATES_DIR="${CODER_DIR}/templates"

echo "Setting up workspace templates..."

# Copy Python 3.13 template
if [ -d "${SCRIPT_DIR}/templates/python3.13" ]; then
  echo "Copying Python 3.13 template..."
  mkdir -p "${TEMPLATES_DIR}/python3.13"
  cp -r "${SCRIPT_DIR}/templates/python3.13/"* "${TEMPLATES_DIR}/python3.13/"
  echo "Python 3.13 template copied."
  HAVE_PYTHON_TEMPLATE=true
else
  echo "Note: Python 3.13 template not found in ${SCRIPT_DIR}/templates/python3.13"
  HAVE_PYTHON_TEMPLATE=false
fi

# Copy MATLAB template
if [ -d "${SCRIPT_DIR}/templates/matlab" ]; then
  echo "Copying MATLAB template..."
  mkdir -p "${TEMPLATES_DIR}/matlab"
  cp -r "${SCRIPT_DIR}/templates/matlab/"* "${TEMPLATES_DIR}/matlab/"
  echo "MATLAB template copied."
  HAVE_MATLAB_TEMPLATE=true
else
  echo "Note: MATLAB template not found in ${SCRIPT_DIR}/templates/matlab"
  HAVE_MATLAB_TEMPLATE=false
fi

###########################
# COPY docker-compose.yml AND CREATE .env
###########################

echo "Copying docker-compose.yml..."
cp "${SCRIPT_DIR}/docker-compose.yml" "${CODER_DIR}/docker-compose.yml"

echo "Copying blocked.conf for Traefik protection..."
cp "${SCRIPT_DIR}/blocked.conf" "${CODER_DIR}/blocked.conf"

echo "Creating .env file from template..."
cp "${SCRIPT_DIR}/.env.example" "${CODER_DIR}/.env"

# Build connection URL in parts
PG_CONN="postgresql://coder:${CODER_POSTGRES_PASSWORD}"
PG_CONN="${PG_CONN}@database:${CODER_POSTGRES_PORT}/coder?sslmode=disable"

# Replace placeholder values in .env
sed -i "s|^CODER_DIR=.*|CODER_DIR=${CODER_DIR}|" "${CODER_DIR}/.env"
sed -i "s|^CODER_PORT=.*|CODER_PORT=${CODER_PORT}|" "${CODER_DIR}/.env"
sed -i "s|^CODER_POSTGRES_PORT=.*|CODER_POSTGRES_PORT=${CODER_POSTGRES_PORT}|" "${CODER_DIR}/.env"
sed -i "s|^CODER_ACCESS_URL=.*|CODER_ACCESS_URL=${CODER_ACCESS_URL}|" "${CODER_DIR}/.env"
sed -i "s|^CODER_PG_CONNECTION_URL=.*|CODER_PG_CONNECTION_URL=${PG_CONN}|" "${CODER_DIR}/.env"
sed -i "s|^DOCKER_GID=.*|DOCKER_GID=${DOCKER_GID}|" "${CODER_DIR}/.env"
sed -i "s|^CODER_ADMIN_USERNAME=.*|CODER_ADMIN_USERNAME=${CODER_ADMIN_USERNAME}|" "${CODER_DIR}/.env"
sed -i "s|^CODER_ADMIN_EMAIL=.*|CODER_ADMIN_EMAIL=${CODER_ADMIN_EMAIL}|" "${CODER_DIR}/.env"
sed -i "s|^CODER_ADMIN_PASSWORD=.*|CODER_ADMIN_PASSWORD=${CODER_ADMIN_PASSWORD}|" "${CODER_DIR}/.env"
sed -i "s|^CODER_ADMIN_API_SECRET=.*|CODER_ADMIN_API_SECRET=${CODER_ADMIN_API_SECRET}|" "${CODER_DIR}/.env"

###########################
# COPY SETUP-ADMIN SCRIPT
###########################

if [ -f "${SCRIPT_DIR}/setup-admin.sh" ]; then
  cp "${SCRIPT_DIR}/setup-admin.sh" "${CODER_DIR}/"
  chmod +x "${CODER_DIR}/setup-admin.sh"
  echo "Admin setup script copied to: ${CODER_DIR}/setup-admin.sh"
fi

###########################
# START CODER
###########################

echo "Starting Coder..."
cd "${CODER_DIR}"
docker compose up -d

echo ""
echo "====================================================="
echo "CODER is running."
echo "Docker GID set to: $DOCKER_GID"
echo "Access URL: $CODER_ACCESS_URL"
echo "Installation directory: $CODER_DIR"
echo ""
echo "Local registry: localhost:5000"
echo "Workspace images:"
echo "  - localhost:5000/computor-workspace-python3.13:latest"
echo "  - localhost:5000/computor-workspace-matlab:latest"
echo ""
echo "Templates:"
if [ "$HAVE_PYTHON_TEMPLATE" = true ]; then
  echo "  - python3.13-workspace (Python 3.13 + code-server)"
fi
if [ "$HAVE_MATLAB_TEMPLATE" = true ]; then
  echo "  - matlab-workspace (MATLAB R2024b + code-server)"
fi
if [ -n "$CODER_ADMIN_USERNAME" ]; then
  echo ""
  echo "Admin user: $CODER_ADMIN_USERNAME ($CODER_ADMIN_EMAIL)"
  echo "Templates will be created automatically."
fi
echo ""
echo "WORKSPACE CREATION PROTECTION:"
echo "  Admin API Secret: $CODER_ADMIN_API_SECRET"
echo "  Use this header to create users/workspaces from your backend:"
echo "    X-Admin-Secret: $CODER_ADMIN_API_SECRET"
echo ""
echo "To create users with specific templates, use:"
echo "  ./create-user.sh -t python3.13-workspace ..."
echo "  ./create-user.sh -t matlab-workspace ..."
echo ""
echo "To create additional admin users later, run:"
echo "  ${CODER_DIR}/setup-admin.sh"
echo "====================================================="
