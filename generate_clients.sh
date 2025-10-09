#!/bin/bash
# Generate TypeScript API client classes from backend interfaces.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

# shellcheck disable=SC1090
source "${ROOT_DIR}/scripts/utilities/ensure_venv.sh"

echo "🛠️  Generating TypeScript API clients..."

ensure_venv

PYTHON_BIN="${PYTHON_BIN:-python}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    PYTHON_BIN="python3"
fi

cd "${ROOT_DIR}" && \
PYTHONPATH="${ROOT_DIR}/computor-backend/src:${ROOT_DIR}/computor-types/src:${ROOT_DIR}/computor-cli/src${PYTHONPATH:+:${PYTHONPATH}}" \
    "${PYTHON_BIN}" -m computor_cli.cli generate-clients "$@"

echo "✅ TypeScript API clients generated successfully!"
echo "📁 Check frontend/src/api/generated/ for the generated files"
