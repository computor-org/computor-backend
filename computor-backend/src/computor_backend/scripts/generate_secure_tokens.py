#!/usr/bin/env python3
"""
Generate secure API tokens for deployment.

This script generates cryptographically secure tokens that can be used
with the --predefined-tokens option when creating service users.

Usage:
    python generate_secure_tokens.py [--count N] [--output-env]

Options:
    --count N       Number of tokens to generate (default: 3)
    --output-env    Output in .env format with suggested variable names

Example:
    # Generate 3 tokens for worker services
    python generate_secure_tokens.py --count 3 --output-env

    # Generate single token
    python generate_secure_tokens.py --count 1
"""

import sys
import argparse
import secrets
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.api_token import TOKEN_PREFIX, TOKEN_RANDOM_LENGTH


def generate_secure_token() -> str:
    """
    Generate a cryptographically secure API token.

    Returns:
        str: Token in format ctp_<32_random_chars>
    """
    random_part = secrets.token_urlsafe(24)[:TOKEN_RANDOM_LENGTH]
    return f"{TOKEN_PREFIX}{random_part}"


def main():
    """Generate secure API tokens."""
    parser = argparse.ArgumentParser(description="Generate secure API tokens for deployment")
    parser.add_argument("--count", type=int, default=3, help="Number of tokens to generate")
    parser.add_argument("--output-env", action="store_true", help="Output in .env format")
    args = parser.parse_args()

    if args.count < 1 or args.count > 100:
        print("❌ Error: Count must be between 1 and 100")
        return 1

    print("\n🔐 Secure Token Generation")
    print("=" * 60)
    print(f"Generating {args.count} secure token(s)...\n")

    service_names = [
        "TEMPORAL_WORKER_PYTHON_TOKEN",
        "TEMPORAL_WORKER_MATLAB_TOKEN",
        "TEMPORAL_WORKER_GENERAL_TOKEN",
    ]

    tokens = [generate_secure_token() for _ in range(args.count)]

    if args.output_env:
        print("📝 Environment Variables (.env format):")
        print("-" * 60)
        for i, token in enumerate(tokens):
            if i < len(service_names):
                print(f"{service_names[i]}={token}")
            else:
                print(f"API_TOKEN_{i+1}={token}")
        print()
    else:
        print("🔑 Generated Tokens:")
        print("-" * 60)
        for i, token in enumerate(tokens, 1):
            print(f"Token {i}: {token}")
        print()

    print("⚠️  SECURITY IMPORTANT:")
    print("   - Store these tokens securely (secrets manager, encrypted vault)")
    print("   - Never commit tokens to version control")
    print("   - Use environment variables or secure configuration")
    print("   - Rotate tokens regularly")
    print()

    if args.output_env:
        print("💡 Usage:")
        print("   1. Add these to your .env file")
        print("   2. Run: cd computor-backend/src && \\")
        print("      python -m computor_backend.scripts.create_service_users \\")
        print("      --predefined-tokens --output-env")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
