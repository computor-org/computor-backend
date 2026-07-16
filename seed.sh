#!/bin/bash
# Development seeder — enrols fake users into EXISTING courses.
#
# Runs the backend's own import logic in-process as an admin, so every real
# mechanic applies (user find-or-create, student profiles, submission groups).
# Seeded users (dev.userNNN@seed.local) are not loginable. Needs Postgres up
# (computor.sh up); does NOT need the API (api.sh) or Keycloak.
#
# Usage:
#   bash seed.sh                          # 20 users into every course
#   bash seed.sh --users 50               # 50 users per course
#   bash seed.sh --course-id <uuid>       # only that course (or --course-path)
#   bash seed.sh --cleanup                # remove seeded users, then reseed
#   bash seed.sh --cleanup-only           # just remove seeded users
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
