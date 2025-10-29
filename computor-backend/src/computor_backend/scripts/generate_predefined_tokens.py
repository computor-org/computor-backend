#!/usr/bin/env python3
"""
Generate predefined API tokens for services.

These tokens can be generated BEFORE the system runs and placed in:
- .env files
- Docker Compose secrets
- deployment.yaml

Usage:
    python generate_predefined_tokens.py

The tokens will be valid when the deployment creates the services with these tokens.
"""

import secrets
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.api_token import generate_api_token


def generate_predefined_token(service_name: str) -> str:
    """
    Generate a predefined API token for a service.

    This uses the same format as the API token generation, so it will be
    valid when the service is created with this token.

    Args:
        service_name: Name of the service (e.g., "python-worker", "matlab-worker")

    Returns:
        str: The generated token (ctp_...)
    """
    full_token, prefix, token_hash = generate_api_token()
    return full_token


def main():
    """Generate predefined tokens for common services."""

    print("🔐 Generating Predefined API Tokens")
    print("=" * 70)
    print()
    print("These tokens can be used in your .env file or deployment.yaml")
    print("BEFORE running the deployment.")
    print()
    print("⚠️  IMPORTANT: Store these tokens securely!")
    print("=" * 70)
    print()

    services = [
        {
            "name": "Python Worker",
            "env_var": "PYTHON_WORKER_TOKEN",
            "description": "Token for temporal-worker-python service"
        },
        {
            "name": "MATLAB Worker",
            "env_var": "MATLAB_WORKER_TOKEN",
            "description": "Token for temporal-worker-matlab service"
        }
    ]

    tokens = {}

    for service in services:
        token = generate_predefined_token(service["name"])
        tokens[service["env_var"]] = token

        print(f"📝 {service['name']}")
        print(f"   Description: {service['description']}")
        print(f"   Environment Variable: {service['env_var']}")
        print(f"   Token: {token}")
        print()

    print("=" * 70)
    print("💾 Copy to your .env file:")
    print("=" * 70)
    print()

    for env_var, token in tokens.items():
        print(f"{env_var}={token}")

    print()
    print("=" * 70)
    print("📋 Usage in deployment.yaml:")
    print("=" * 70)
    print()
    print("services:")
    print("  - slug: itpcp.exec.py")
    print("    api_token:")
    print(f"      token: \"${{{list(tokens.keys())[0]}}}\"")
    print()
    print("  - slug: itpcp.exec.mat")
    print("    api_token:")
    print(f"      token: \"${{{list(tokens.keys())[1]}}}\"")
    print()
    print("=" * 70)
    print("✅ Done! Store these tokens in a secure location.")
    print("=" * 70)


if __name__ == "__main__":
    main()
