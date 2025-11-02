"""
API Token generation and validation utilities.

Provides secure token generation, hashing, and verification for API authentication.
"""

import secrets
import hashlib
from typing import Tuple


# Token format: ctp_<random_32_chars>
# Example: ctp_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
TOKEN_PREFIX = "ctp_"
TOKEN_RANDOM_LENGTH = 32


def generate_api_token() -> Tuple[str, str, bytes]:
    """
    Generate a new API token with prefix and hash.

    The token is generated using cryptographically secure random bytes.
    Only the hash is stored in the database for security.

    IMPORTANT: When storing in the database, you MUST check for hash uniqueness
    and retry generation if a collision occurs (though statistically very unlikely).

    Token entropy: 32 characters of base64 = ~192 bits of entropy.
    Collision probability is negligible (< 2^-96 for millions of tokens).

    Returns:
        tuple: (full_token, prefix, token_hash)
            - full_token: The complete token string to give to the user (store securely!)
            - prefix: First 12 characters for identification (e.g., "ctp_a1b2c3d4")
            - token_hash: SHA-256 hash for database storage (check uniqueness!)

    Example:
        >>> token, prefix, token_hash = generate_api_token()
        >>> print(f"Token: {token}")
        Token: ctp_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
        >>> print(f"Prefix: {prefix}")
        Prefix: ctp_a1b2c3d4
        >>> print(f"Hash length: {len(token_hash)}")
        Hash length: 32

    Usage with database (handling uniqueness):
        >>> from sqlalchemy.exc import IntegrityError
        >>> max_retries = 5
        >>> for attempt in range(max_retries):
        ...     token, prefix, token_hash = generate_api_token()
        ...     try:
        ...         api_token = ApiToken(token_hash=token_hash, ...)
        ...         db.add(api_token)
        ...         db.flush()  # Check uniqueness constraint
        ...         break  # Success
        ...     except IntegrityError:
        ...         db.rollback()
        ...         if attempt == max_retries - 1:
        ...             raise  # Give up after max retries
    """
    # Generate cryptographically secure random bytes
    # We use url-safe base64 encoding which produces [A-Za-z0-9_-] characters
    random_part = secrets.token_urlsafe(24)[:TOKEN_RANDOM_LENGTH]

    # Construct full token
    full_token = f"{TOKEN_PREFIX}{random_part}"

    # Extract prefix (first 12 chars for display/identification)
    prefix = full_token[:12]

    # Hash token for secure storage (SHA-256)
    token_hash = hashlib.sha256(full_token.encode('utf-8')).digest()

    return full_token, prefix, token_hash


def hash_api_token(token: str) -> bytes:
    """
    Hash an API token using SHA-256.

    Args:
        token: The full API token string

    Returns:
        bytes: SHA-256 hash of the token

    Example:
        >>> token = "ctp_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
        >>> token_hash = hash_api_token(token)
        >>> len(token_hash)
        32
    """
    return hashlib.sha256(token.encode('utf-8')).digest()


def verify_api_token(token: str, stored_hash: bytes) -> bool:
    """
    Verify an API token against its stored hash.

    Args:
        token: The full API token string provided by the user
        stored_hash: The SHA-256 hash stored in the database

    Returns:
        bool: True if token matches the hash, False otherwise

    Example:
        >>> token, prefix, token_hash = generate_api_token()
        >>> verify_api_token(token, token_hash)
        True
        >>> verify_api_token("wrong_token", token_hash)
        False
    """
    computed_hash = hash_api_token(token)
    return secrets.compare_digest(computed_hash, stored_hash)


def validate_token_format(token: str) -> bool:
    """
    Validate that a token has the correct format.

    Args:
        token: The token string to validate

    Returns:
        bool: True if token format is valid, False otherwise

    Example:
        >>> validate_token_format("ctp_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6")
        True
        >>> validate_token_format("invalid_token")
        False
        >>> validate_token_format("ctp_short")
        False
    """
    if not token.startswith(TOKEN_PREFIX):
        return False

    if len(token) != len(TOKEN_PREFIX) + TOKEN_RANDOM_LENGTH:
        return False

    # Check that the random part contains only valid url-safe base64 chars
    random_part = token[len(TOKEN_PREFIX):]
    valid_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-')
    return all(c in valid_chars for c in random_part)


def prepare_predefined_token(token: str) -> Tuple[str, str, bytes]:
    """
    Prepare a pre-defined API token for storage.

    Use this when you want to set a specific token value (e.g., from configuration
    or environment variables). This is useful for deployment scenarios where workers
    need known token values that can be configured before the system starts.

    SECURITY WARNING: Pre-defined tokens must be:
    - Generated securely (e.g., using `secrets.token_urlsafe()`)
    - Stored securely (e.g., in secrets management, encrypted env files)
    - Never hardcoded in source code or committed to version control

    Args:
        token: The predefined token string (must start with 'ctp_' and be 36 chars total)

    Returns:
        tuple: (full_token, prefix, token_hash)
            - full_token: The provided token (validated)
            - token_prefix: First 12 characters for display
            - token_hash: SHA-256 hash for database storage

    Raises:
        ValueError: If token format is invalid

    Example:
        >>> # In deployment config or secure env var:
        >>> token = "ctp_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
        >>> full_token, prefix, token_hash = prepare_predefined_token(token)
        >>> print(f"Prefix: {prefix}")
        Prefix: ctp_a1b2c3d4
    """
    if not validate_token_format(token):
        raise ValueError(
            f"Invalid token format. Token must:\n"
            f"  - Start with '{TOKEN_PREFIX}'\n"
            f"  - Be exactly {len(TOKEN_PREFIX) + TOKEN_RANDOM_LENGTH} characters long\n"
            f"  - Contain only URL-safe base64 characters (A-Za-z0-9_-)\n"
            f"  Example: ctp_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
        )

    # Extract prefix (first 12 chars for display/identification)
    prefix = token[:12]

    # Hash token for secure storage (SHA-256)
    token_hash = hashlib.sha256(token.encode('utf-8')).digest()

    return token, prefix, token_hash
