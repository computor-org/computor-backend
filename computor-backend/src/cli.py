#!/usr/bin/env python3
"""
DEPRECATED: CLI moved to computor-cli package.
Use: computor <command> instead of python computor-backend/src/cli.py <command>

This file redirects to the new CLI for backwards compatibility.
"""

import sys
import os

# Add computor-cli to path
cli_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'computor-cli', 'src')
sys.path.insert(0, cli_path)

try:
    from computor_cli.cli import cli

    if __name__ == '__main__':
        print("⚠️  WARNING: This CLI entry point is deprecated.", file=sys.stderr)
        print("⚠️  Please use 'computor' command instead.", file=sys.stderr)
        print("⚠️  Example: computor deployment apply deployment.yaml", file=sys.stderr)
        print("", file=sys.stderr)
        cli()
except ImportError as e:
    print(f"❌ Error: Could not import CLI from computor-cli package: {e}", file=sys.stderr)
    print("", file=sys.stderr)
    print("Please install the computor-cli package:", file=sys.stderr)
    print("  cd computor-cli && pip install -e .", file=sys.stderr)
    print("", file=sys.stderr)
    print("Or use the 'computor' command directly.", file=sys.stderr)
    sys.exit(1)