#!/bin/bash
# Development database seeder.
#
# Creates fake users and enrols them into EXISTING courses with a role mix so
# you have realistic rosters in the web UI and the VS Code extension. Direct-DB
# only (no Keycloak/Forgejo) — seeded users appear in rosters but cannot log in.
# Every seeded row is tagged properties.dev_seed for a clean --cleanup.
#
# Usage:
#   bash seed.sh                          # 20 users into every course
#   bash seed.sh --users 50               # 50 users per course
#   bash seed.sh --course-path py-2025    # only that course
#   bash seed.sh --cleanup                # remove seeded rows, then reseed
#   bash seed.sh --cleanup-only           # just remove seeded rows
#   bash seed.sh --help                   # full option list

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

# shellcheck disable=SC1090
source "${ROOT_DIR}/scripts/utilities/ensure_venv.sh"
ensure_venv

PYTHON_BIN="${PYTHON_BIN:-python}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    PYTHON_BIN="python3"
fi

export PYTHONPATH="${ROOT_DIR}/computor-backend/src:${ROOT_DIR}/computor-types/src${PYTHONPATH:+:${PYTHONPATH}}"

cd "${ROOT_DIR}" && \
    exec "${PYTHON_BIN}" "${ROOT_DIR}/computor-backend/src/computor_backend/scripts/seed_dev.py" "$@"
