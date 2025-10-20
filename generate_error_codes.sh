#!/bin/bash

# Generate error code definitions for all platforms
# This script generates TypeScript, JSON, Markdown, and Python error code files
# from the error_registry.yaml source of truth

set -e

echo "=========================================="
echo "Computor Error Code Generator"
echo "=========================================="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required but not installed."
    exit 1
fi

# Check if error_registry.yaml exists
if [ ! -f "computor-backend/error_registry.yaml" ]; then
    echo "Error: error_registry.yaml not found in computor-backend/"
    exit 1
fi

# Install required Python packages if needed
echo "Checking dependencies..."
python3 -c "import yaml" 2>/dev/null || {
    echo "Installing PyYAML..."
    pip install pyyaml
}

# Run the generator
echo "Running error code generator..."
python3 generate_error_codes.py

echo ""
echo "=========================================="
echo "Error code generation complete!"
echo "=========================================="
