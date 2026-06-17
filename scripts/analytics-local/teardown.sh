#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib.sh"

echo "Stopping source analytics instance (${ANALYTICS_LOCAL_SOURCE_PROJECT})"
compose_source down --remove-orphans

echo "Stopping blue analytics instance (${ANALYTICS_LOCAL_BLUE_PROJECT})"
compose_blue down --remove-orphans

remove_data_root

echo "Removed local analytics data root: ${ANALYTICS_LOCAL_DATA_ROOT}"
