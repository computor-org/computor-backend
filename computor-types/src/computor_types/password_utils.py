"""
Secure password hashing and validation utilities using Argon2.

This module provides password hashing functionality using Argon2id,
the winner of the Password Hashing Competition and current industry
best practice for password storage.

Key Features:
- One-way hashing (passwords cannot be decrypted)
- Automatic per-password salt generation
- Configurable complexity requirements
- Protection against timing attacks
- Future-proof design with parameter upgrading support

Security Notes:
- Passwords are NEVER stored in plaintext or reversibly encrypted
- Each password gets a unique salt automatically
- Argon2id provides resistance to GPU/ASIC cracking attacks
- Hashing is intentionally slow to prevent brute-force attacks

Example Usage:
    >>> from computor_types.password_utils import hash_password, verify_password
    >>>
    >>> # Hash a password
    >>> hashed = hash_password("MySecure123!")
    >>>
    >>> # Verify a password
    >>> if verify_password("MySecure123!", hashed):
    ...     print("Password correct!")
    >>>
    >>> # Validate password strength before hashing
    >>> from computor_types.password_utils import validate_password_strength
    >>> validate_password_strength("weak")  # Raises PasswordValidationError
"""

import re
from typing import Optional, List
from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHash


# Initialize Argon2 hasher with secure parameters
# Based on OWASP recommendations and Argon2 RFC 9106
_ph = PasswordHasher(
    time_cost=3,        # Number of iterations (3 = ~100ms on modern CPU)
    memory_cost=65536,  # 64 MB memory usage (prevents GPU attacks)
    parallelism=4,      # Number of parallel threads
    hash_len=32,        # Length of hash in bytes (256 bits)
    salt_len=16,        # Length of salt in bytes (128 bits)
)


@dataclass
class PasswordValidationError(Exception):
    """Exception raised when password validation fails."""
    message: str
    code: str

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class PasswordComplexityRequirements:
    """
    Configurable password complexity requirements.

    Based on NIST SP 800-63B and OWASP ASVS guidelines.
    """

    # Minimum length (NIST recommends 8+, we use 12 for better security)
    MIN_LENGTH = 12

    # Maximum length (prevent DoS via extremely long passwords)
    MAX_LENGTH = 128

    # Require at least one uppercase letter
    REQUIRE_UPPERCASE = True

    # Require at least one lowercase letter
    REQUIRE_LOWERCASE = True

    # Require at least one digit
    REQUIRE_DIGIT = True

    # Require at least one special character
    REQUIRE_SPECIAL = True

    # Special characters allowed
    SPECIAL_CHARACTERS = "!@#$%^&*()_+-=[]{}|;:,.<>?"

    # Common passwords to reject (add more as needed)
    COMMON_PASSWORDS = {
        "password123", "Password123", "Password123!",
        "admin123", "Admin123", "Admin123!",
        "Welcome123", "Welcome123!",
        "Qwerty123", "Qwerty123!",
        "123456789", "12345678",
        "computor123", "Computor123", "Computor123!",
    }

    # Sequences to reject
    REJECT_SEQUENCES = [
        "12345", "abcde", "qwerty", "asdfg",
    ]


def validate_password_strength(
    password: str,
    username: Optional[str] = None,
    email: Optional[str] = None,
    custom_forbidden_words: Optional[List[str]] = None,
) -> None:
    """
    Validate password meets complexity requirements.

    This function checks password strength according to modern security
    best practices (NIST SP 800-63B, OWASP ASVS).

    Args:
        password: The password to validate
        username: Optional username to prevent password == username
        email: Optional email to prevent password containing email parts
        custom_forbidden_words: Optional list of organization-specific forbidden words

    Raises:
        PasswordValidationError: If password doesn't meet requirements

    Example:
        >>> validate_password_strength("MySecure123!")  # OK
        >>> validate_password_strength("weak")  # Raises error
        >>> validate_password_strength("john", username="john")  # Raises error
    """
    errors = []

    # 1. Length requirements
    if len(password) < PasswordComplexityRequirements.MIN_LENGTH:
        raise PasswordValidationError(
            message=f"Password must be at least {PasswordComplexityRequirements.MIN_LENGTH} characters long",
            code="PASSWORD_TOO_SHORT"
        )

    if len(password) > PasswordComplexityRequirements.MAX_LENGTH:
        raise PasswordValidationError(
            message=f"Password must not exceed {PasswordComplexityRequirements.MAX_LENGTH} characters",
            code="PASSWORD_TOO_LONG"
        )

    # 2. Complexity requirements
    if PasswordComplexityRequirements.REQUIRE_UPPERCASE:
        if not any(c.isupper() for c in password):
            errors.append("at least one uppercase letter (A-Z)")

    if PasswordComplexityRequirements.REQUIRE_LOWERCASE:
        if not any(c.islower() for c in password):
            errors.append("at least one lowercase letter (a-z)")

    if PasswordComplexityRequirements.REQUIRE_DIGIT:
        if not any(c.isdigit() for c in password):
            errors.append("at least one digit (0-9)")

    if PasswordComplexityRequirements.REQUIRE_SPECIAL:
        if not any(c in PasswordComplexityRequirements.SPECIAL_CHARACTERS for c in password):
            errors.append(f"at least one special character ({PasswordComplexityRequirements.SPECIAL_CHARACTERS})")

    if errors:
        raise PasswordValidationError(
            message=f"Password must contain: {', '.join(errors)}",
            code="PASSWORD_COMPLEXITY_FAILED"
        )

    # 3. Common password check
    password_lower = password.lower()
    if password in PasswordComplexityRequirements.COMMON_PASSWORDS:
        raise PasswordValidationError(
            message="This password is too common. Please choose a more unique password.",
            code="PASSWORD_TOO_COMMON"
        )

    # 4. Sequence check
    for sequence in PasswordComplexityRequirements.REJECT_SEQUENCES:
        if sequence in password_lower:
            raise PasswordValidationError(
                message="Password contains a common sequence. Please choose a more complex password.",
                code="PASSWORD_CONTAINS_SEQUENCE"
            )

    # 5. Username similarity check
    if username and len(username) >= 3:
        if username.lower() in password_lower:
            raise PasswordValidationError(
                message="Password must not contain your username",
                code="PASSWORD_CONTAINS_USERNAME"
            )

    # 6. Email similarity check
    if email:
        email_parts = email.split('@')[0].lower()
        if len(email_parts) >= 3 and email_parts in password_lower:
            raise PasswordValidationError(
                message="Password must not contain parts of your email address",
                code="PASSWORD_CONTAINS_EMAIL"
            )

    # 7. Custom forbidden words
    if custom_forbidden_words:
        for word in custom_forbidden_words:
            if word.lower() in password_lower:
                raise PasswordValidationError(
                    message="Password contains a forbidden word",
                    code="PASSWORD_CONTAINS_FORBIDDEN_WORD"
                )

    # 8. All the same character check
    if len(set(password)) <= 2:
        raise PasswordValidationError(
            message="Password must contain more variety of characters",
            code="PASSWORD_TOO_REPETITIVE"
        )


def hash_password(password: str) -> str:
    """
    Hash a password using Argon2id.

    This function creates a secure one-way hash of the password.
    The password CANNOT be recovered from the hash (by design).

    Each password automatically gets a unique random salt, so the same
    password will produce different hashes each time.

    Args:
        password: Plain text password to hash

    Returns:
        Argon2 hash string in PHC format:
        $argon2id$v=19$m=65536,t=3,p=4$<salt>$<hash>

    Example:
        >>> hashed = hash_password("MySecure123!")
        >>> print(hashed)
        $argon2id$v=19$m=65536,t=3,p=4$...

    Note:
        The returned hash includes:
        - Algorithm identifier (argon2id)
        - Version (v=19)
        - Parameters (memory=65536, time=3, parallelism=4)
        - Random salt (base64 encoded)
        - Resulting hash (base64 encoded)
    """
    return _ph.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    This function performs constant-time comparison to prevent
    timing attacks.

    Args:
        password: Plain text password to verify
        hashed_password: Argon2 hash to verify against

    Returns:
        True if password matches hash, False otherwise

    Example:
        >>> hashed = hash_password("MySecure123!")
        >>> verify_password("MySecure123!", hashed)
        True
        >>> verify_password("WrongPassword!", hashed)
        False

    Security:
        - Comparison time is constant regardless of password correctness
        - Prevents timing-based password guessing attacks
        - Safe to use in authentication systems
    """
    try:
        _ph.verify(hashed_password, password)
        return True
    except (VerifyMismatchError, VerificationError, InvalidHash):
        return False


def needs_rehash(hashed_password: str) -> bool:
    """
    Check if a password hash needs to be rehashed with updated parameters.

    This is useful when you upgrade Argon2 parameters (e.g., increase
    memory cost) and want to upgrade old hashes on next user login.

    Args:
        hashed_password: Argon2 hash to check

    Returns:
        True if hash should be regenerated with current parameters

    Example:
        >>> # On successful login:
        >>> if verify_password(password, stored_hash):
        ...     if needs_rehash(stored_hash):
        ...         # Upgrade to new parameters
        ...         new_hash = hash_password(password)
        ...         update_stored_hash(new_hash)

    Use Case:
        When you increase security parameters in the future, this
        function lets you transparently upgrade user passwords
        without forcing a password reset.
    """
    try:
        return _ph.check_needs_rehash(hashed_password)
    except (VerificationError, InvalidHash):
        # If hash is invalid/corrupted, it definitely needs rehashing
        return True


def is_argon2_hash(value: str) -> bool:
    """
    Check if a string is a valid Argon2 hash.

    Useful during migration from old password storage to determine
    which verification method to use.

    Args:
        value: String to check

    Returns:
        True if string appears to be an Argon2 hash

    Example:
        >>> is_argon2_hash("$argon2id$v=19$m=65536...")
        True
        >>> is_argon2_hash("old_encrypted_password")
        False
    """
    return value.startswith("$argon2")


# Simplified API for common use cases
def create_password_hash(password: str, validate: bool = True, **validation_kwargs) -> str:
    """
    Convenience function to validate and hash password in one step.

    Args:
        password: Plain text password
        validate: Whether to validate password strength (default: True)
        **validation_kwargs: Additional arguments for validate_password_strength()

    Returns:
        Argon2 hash string

    Raises:
        PasswordValidationError: If validation fails

    Example:
        >>> hash = create_password_hash("MySecure123!", username="john")
        >>> # Same as:
        >>> # validate_password_strength("MySecure123!", username="john")
        >>> # hash = hash_password("MySecure123!")
    """
    if validate:
        validate_password_strength(password, **validation_kwargs)
    return hash_password(password)
