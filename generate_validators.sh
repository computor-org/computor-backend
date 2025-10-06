#!/bin/bash
# Generate TypeScript validation classes from Pydantic models.
# This script:
# 1. Exports JSON schemas from Pydantic models
# 2. Generates TypeScript validation classes from schemas

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

# shellcheck disable=SC1090
source "${ROOT_DIR}/scripts/utilities/ensure_venv.sh"

echo "🚀 Generating TypeScript Validation Classes..."

ensure_venv

PYTHON_BIN="${PYTHON_BIN:-python}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    PYTHON_BIN="python3"
fi

# Generate validators with schema export
PYTHONPATH="${ROOT_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}" \
    "${PYTHON_BIN}" -m computor_backend.cli.cli generate-validators --export-schemas "$@"

echo "✅ Validation classes generated successfully!"
echo "📁 Schemas: frontend/src/types/schemas/"
echo "📁 Validators: frontend/src/types/validators/"