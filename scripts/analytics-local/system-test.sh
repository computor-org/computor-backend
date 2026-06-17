#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib.sh"

wait_for_postgres source compose_source
wait_for_postgres blue compose_blue

analytics_root="${ANALYTICS_LOCAL_DATA_ROOT}/blue/analytics"
if [[ "$ANALYTICS_LOCAL_DATA_ROOT" != /* || "$ANALYTICS_LOCAL_DATA_ROOT" == "/" ]]; then
    echo "Refusing to use unsafe data root: ${ANALYTICS_LOCAL_DATA_ROOT}" >&2
    exit 1
fi
if [[ "$analytics_root" != */blue/analytics ]]; then
    echo "Refusing to clean unexpected analytics root: ${analytics_root}" >&2
    exit 1
fi
rm -rf -- "$analytics_root"
mkdir -p "$analytics_root"

source_database_url="postgresql+psycopg2://${ANALYTICS_LOCAL_READER_USER}:${ANALYTICS_LOCAL_READER_PASSWORD}@127.0.0.1:${ANALYTICS_LOCAL_SOURCE_POSTGRES_PORT}/${ANALYTICS_LOCAL_POSTGRES_DB}"

echo "Running analytics import system test"
PYTHONPATH="${REPO_ROOT}/computor-backend/src:${REPO_ROOT}/computor-types/src${PYTHONPATH:+:${PYTHONPATH}}" \
ANALYTICS_ROOT="$analytics_root" \
ANALYTICS_SOURCE_DATABASE_URL="$source_database_url" \
uv run --python 3.11 --project "${REPO_ROOT}/computor-backend" \
    python "${SCRIPT_DIR}/system_test.py"
