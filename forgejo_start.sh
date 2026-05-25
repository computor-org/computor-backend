#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -f "$SCRIPT_DIR/forgejo/.env" ]; then
    echo "Error: forgejo/.env not found. Copy forgejo/.env.example to forgejo/.env and fill in values."
    exit 1
fi

docker compose \
    -f "$SCRIPT_DIR/forgejo/docker-compose.yml" \
    --env-file "$SCRIPT_DIR/forgejo/.env" \
    up -d
