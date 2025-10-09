#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

# shellcheck disable=SC1090
source "${ROOT_DIR}/scripts/utilities/ensure_venv.sh"

echo "🔧 Generating JSON Schema for meta.yaml files..."

ensure_venv

PYTHON_BIN="${PYTHON_BIN:-python}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    PYTHON_BIN="python3"
fi

cd "${ROOT_DIR}" && \
PYTHONPATH="${ROOT_DIR}/computor-backend/src:${ROOT_DIR}/computor-types/src:${ROOT_DIR}/computor-cli/src${PYTHONPATH:+:${PYTHONPATH}}" \
    "${PYTHON_BIN}" -m computor_cli.cli generate-schema "$@"

echo "✅ JSON Schema generation completed successfully!"
