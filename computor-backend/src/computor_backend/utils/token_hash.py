"""Token hashing utilities for secure storage."""

import hashlib
import secrets
from typing import Union


def hash_token(token: str) -> str:
    """
    Hash a token using SHA-256 for secure storage.
    Returns hex digest (64 chars) suitable for String columns.
    
    Args:
        token: Plain token string
        
    Returns:
        Hex string of SHA-256 hash
    """
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def hash_token_binary(token: str) -> bytes:
    """
    Hash a token using SHA-256 for secure storage.
    Returns binary digest for LargeBinary columns.
    
    Args:
        token: Plain token string
        
    Returns:
        Binary bytes of SHA-256 hash
    """
    return hashlib.sha256(token.encode('utf-8')).digest()


def generate_token(length: int = 32) -> str:
    """
    Generate a secure random token.
    
    Args:
        length: Number of random bytes (default 32)
        
    Returns:
        URL-safe base64-encoded token
    """
    return secrets.token_urlsafe(length)


def verify_token_hash(token: str, token_hash: Union[str, bytes]) -> bool:
    """
    Verify a token matches its hash.
    
    Args:
        token: Plain token string
        token_hash: Either hex string or binary hash to compare against
        
    Returns:
        True if token matches hash
    """
    if isinstance(token_hash, bytes):
        return hashlib.sha256(token.encode('utf-8')).digest() == token_hash
    return hash_token(token) == token_hash
