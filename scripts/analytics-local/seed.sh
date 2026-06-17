#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib.sh"

wait_for_postgres source compose_source

echo "Seeding source analytics database"
psql_source_admin < "${SCRIPT_DIR}/seed/source.sql"

echo "Source analytics seed complete"
