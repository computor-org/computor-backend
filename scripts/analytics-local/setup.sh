#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib.sh"

mkdir -p "${ANALYTICS_LOCAL_DATA_ROOT}/source" "${ANALYTICS_LOCAL_DATA_ROOT}/blue"

echo "Starting source analytics instance (${ANALYTICS_LOCAL_SOURCE_PROJECT})"
compose_source up -d

echo "Starting blue analytics instance (${ANALYTICS_LOCAL_BLUE_PROJECT})"
compose_blue up -d

wait_for_postgres source compose_source
wait_for_postgres blue compose_blue

cat <<EOF
Local analytics instances are running.

Source:
  Postgres: 127.0.0.1:${ANALYTICS_LOCAL_SOURCE_POSTGRES_PORT}
  Redis:    127.0.0.1:${ANALYTICS_LOCAL_SOURCE_REDIS_PORT}
  MinIO:    http://127.0.0.1:${ANALYTICS_LOCAL_SOURCE_MINIO_API_PORT}

Blue:
  Postgres: 127.0.0.1:${ANALYTICS_LOCAL_BLUE_POSTGRES_PORT}
  Redis:    127.0.0.1:${ANALYTICS_LOCAL_BLUE_REDIS_PORT}
  MinIO:    http://127.0.0.1:${ANALYTICS_LOCAL_BLUE_MINIO_API_PORT}

Data root: ${ANALYTICS_LOCAL_DATA_ROOT}
EOF
