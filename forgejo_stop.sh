#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

docker compose \
    -f "$SCRIPT_DIR/forgejo/docker-compose.yml" \
    --env-file "$SCRIPT_DIR/forgejo/.env" \
    down "$@"
