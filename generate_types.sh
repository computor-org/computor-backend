#!/bin/bash
# Generate TypeScript interfaces from Pydantic models via the CLI helper.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

# shellcheck disable=SC1090
source "${ROOT_DIR}/scripts/utilities/ensure_venv.sh"

echo "🚀 Generating TypeScript interfaces from Pydantic models..."

ensure_venv

PYTHON_BIN="${PYTHON_BIN:-python}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    PYTHON_BIN="python3"
fi

cd "${ROOT_DIR}" && \
PYTHONPATH="${ROOT_DIR}/computor-backend/src:${ROOT_DIR}/computor-types/src:${ROOT_DIR}/computor-cli/src${PYTHONPATH:+:${PYTHONPATH}}" \
    "${PYTHON_BIN}" -m computor_cli.cli generate-types "$@"

echo "✅ TypeScript interfaces generated successfully!"
echo "📁 Check frontend/src/types/generated/ for the generated files"
