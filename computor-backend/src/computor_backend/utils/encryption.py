"""Reversible encryption for *retrievable* secrets — e.g. git service tokens.

This is deliberately distinct from password storage: passwords must be one-way
hashed (see ``password_utils`` / Argon2) and never decrypted. A git service
token, by contrast, MUST be recoverable so the backend can authenticate to the
remote git server — so it is symmetrically encrypted with ``TOKEN_SECRET``.

Wire-compatible with the legacy ``encrypt_api_key`` / ``decrypt_api_key``
encryption (same ``keycove`` primitive, same ``TOKEN_SECRET`` key), so secrets
encrypted by either round-trip through both.
"""
import os

from keycove import decrypt, encrypt


def _token_secret() -> str:
    """Read the symmetric key lazily so import never fails before env is loaded."""
    key = os.environ.get("TOKEN_SECRET")
    if not key:
        raise RuntimeError(
            "TOKEN_SECRET is not set; cannot encrypt/decrypt retrievable secrets."
        )
    return key


def encrypt_secret(plaintext: str) -> str:
    """Encrypt a retrievable secret (e.g. a git service token) for storage."""
    return encrypt(plaintext, _token_secret())


def decrypt_secret(ciphertext: str) -> str:
    """Decrypt a secret produced by :func:`encrypt_secret` (or the legacy
    ``encrypt_api_key`` — they are wire-compatible)."""
    return decrypt(ciphertext, _token_secret())
