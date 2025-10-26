"""
⚠️ DEPRECATED: Password encryption functions

This module contains DEPRECATED password encryption functions.
DO NOT USE for new code.

SECURITY ISSUE:
These functions use REVERSIBLE encryption for passwords, which is a
security vulnerability. Passwords should NEVER be stored in a way
that allows decryption.

MIGRATION:
This module is kept temporarily for backward compatibility during
migration to Argon2 password hashing (see password_utils.py).

TODO: Remove this module after all passwords have been migrated to Argon2

Replacement:
    from computor_types.password_utils import hash_password, verify_password

    # Old way (INSECURE):
    encrypted = encrypt_api_key(password)  # ❌ Don't use
    decrypted = decrypt_api_key(encrypted)  # ❌ Don't use

    # New way (SECURE):
    hashed = hash_password(password)  # ✅ Use this
    is_valid = verify_password(password, hashed)  # ✅ Use this
"""

import os
import warnings
from keycove import encrypt, decrypt

# Issue deprecation warning when module is imported
warnings.warn(
    "computor_types.tokens module is DEPRECATED. "
    "Password encryption is insecure. "
    "Use computor_types.password_utils for Argon2 hashing instead.",
    DeprecationWarning,
    stacklevel=2
)

secret_key = os.environ.get("TOKEN_SECRET")


def decrypt_api_key(api_key: str):
    """
    DEPRECATED: Decrypt password (INSECURE).

    This function decrypts passwords, which is a security vulnerability.
    Passwords should be hashed, not encrypted.

    Use verify_password() from password_utils instead.
    """
    warnings.warn(
        "decrypt_api_key() is DEPRECATED and INSECURE. Use verify_password() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return decrypt(api_key, secret_key)


def encrypt_api_key(api_key: str):
    """
    DEPRECATED: Encrypt password (INSECURE).

    This function encrypts passwords, which is a security vulnerability.
    Passwords should be hashed, not encrypted.

    Use hash_password() from password_utils instead.
    """
    warnings.warn(
        "encrypt_api_key() is DEPRECATED and INSECURE. Use hash_password() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return encrypt(api_key, secret_key)

