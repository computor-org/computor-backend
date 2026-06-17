#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cleanup() {
    bash "${SCRIPT_DIR}/teardown.sh"
}

trap cleanup EXIT

bash "${SCRIPT_DIR}/setup.sh"
bash "${SCRIPT_DIR}/seed.sh"
bash "${SCRIPT_DIR}/test.sh"
