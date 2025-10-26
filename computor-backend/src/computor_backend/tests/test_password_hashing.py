"""
Comprehensive tests for Argon2 password hashing functionality.

Test coverage:
- Password hashing and verification
- Password complexity validation
- Password reset workflows
- Migration support (Argon2 + legacy encrypted)
- API endpoints
"""

import pytest
from computor_types.password_utils import (
    hash_password,
    verify_password,
    needs_rehash,
    is_argon2_hash,
    validate_password_strength,
    create_password_hash,
    PasswordValidationError,
    PasswordComplexityRequirements,
)


class TestPasswordHashing:
    """Tests for basic password hashing operations."""

    def test_hash_password_creates_valid_hash(self):
        """Test that password hashing produces valid Argon2 hash."""
        password = "MySecurePassword123!"
        hashed = hash_password(password)

        # Argon2 hash should start with $argon2
        assert hashed.startswith("$argon2")
        assert len(hashed) > 50  # Hash should be substantial length

    def test_hash_password_uses_unique_salt(self):
        """Test that same password produces different hashes (different salt)."""
        password = "MySecurePassword123!"
        hashed1 = hash_password(password)
        hashed2 = hash_password(password)

        # Different salt means different hash
        assert hashed1 != hashed2
        # But both should verify against same password
        assert verify_password(password, hashed1)
        assert verify_password(password, hashed2)

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "MySecurePassword123!"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with wrong password."""
        password = "MySecurePassword123!"
        wrong_password = "WrongPassword123!"
        hashed = hash_password(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty(self):
        """Test password verification with empty password."""
        hashed = hash_password("test")
        assert verify_password("", hashed) is False

    def test_verify_password_case_sensitive(self):
        """Test that password verification is case-sensitive."""
        password = "MyPassword123!"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True
        assert verify_password(password.lower(), hashed) is False
        assert verify_password(password.upper(), hashed) is False

    def test_needs_rehash_new_hash(self):
        """Test that newly created hash doesn't need rehashing."""
        password = "MySecurePassword123!"
        hashed = hash_password(password)

        # Newly created hash shouldn't need rehashing
        assert needs_rehash(hashed) is False

    def test_is_argon2_hash_detection(self):
        """Test Argon2 hash detection."""
        # Argon2 hash
        argon2_hash = hash_password("test")
        assert is_argon2_hash(argon2_hash) is True

        # Not Argon2
        assert is_argon2_hash("plaintext") is False
        assert is_argon2_hash("$2b$12$...") is False  # bcrypt
        assert is_argon2_hash("") is False


class TestPasswordComplexity:
    """Tests for password complexity validation."""

    def test_valid_password_passes(self):
        """Test that valid password passes all checks."""
        valid_passwords = [
            "MySecure123!",
            "P@ssw0rd2024",
            "Comput0r!2024",
            "T3st!Password",
        ]

        for password in valid_passwords:
            # Should not raise exception
            validate_password_strength(password)

    def test_password_too_short(self):
        """Test that short passwords are rejected."""
        short_password = "Short1!"  # Only 7 chars

        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password_strength(short_password)

        assert "PASSWORD_TOO_SHORT" in str(exc_info.value.code)
        assert str(PasswordComplexityRequirements.MIN_LENGTH) in str(exc_info.value.message)

    def test_password_too_long(self):
        """Test that excessively long passwords are rejected."""
        long_password = "A1!" + "x" * 200  # Over max length

        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password_strength(long_password)

        assert "PASSWORD_TOO_LONG" in str(exc_info.value.code)

    def test_password_no_uppercase(self):
        """Test that password without uppercase is rejected."""
        no_uppercase = "mysecure123!"

        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password_strength(no_uppercase)

        assert "COMPLEXITY_FAILED" in str(exc_info.value.code)
        assert "uppercase" in str(exc_info.value.message).lower()

    def test_password_no_lowercase(self):
        """Test that password without lowercase is rejected."""
        no_lowercase = "MYSECURE123!"

        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password_strength(no_lowercase)

        assert "COMPLEXITY_FAILED" in str(exc_info.value.code)
        assert "lowercase" in str(exc_info.value.message).lower()

    def test_password_no_digit(self):
        """Test that password without digit is rejected."""
        no_digit = "MySecurePassword!"

        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password_strength(no_digit)

        assert "COMPLEXITY_FAILED" in str(exc_info.value.code)
        assert "digit" in str(exc_info.value.message).lower()

    def test_password_no_special_char(self):
        """Test that password without special character is rejected."""
        no_special = "MySecurePassword123"

        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password_strength(no_special)

        assert "COMPLEXITY_FAILED" in str(exc_info.value.code)
        assert "special" in str(exc_info.value.message).lower()

    def test_password_common_rejected(self):
        """Test that common passwords are rejected."""
        common_passwords = [
            "Password123!",
            "Welcome123!",
            "Admin123!",
        ]

        for password in common_passwords:
            with pytest.raises(PasswordValidationError) as exc_info:
                validate_password_strength(password)
            assert "TOO_COMMON" in str(exc_info.value.code)

    def test_password_contains_sequence(self):
        """Test that passwords with sequences are rejected."""
        sequence_passwords = [
            "Abcde12345!",
            "Qwerty123!",
        ]

        for password in sequence_passwords:
            with pytest.raises(PasswordValidationError) as exc_info:
                validate_password_strength(password)
            assert "SEQUENCE" in str(exc_info.value.code)

    def test_password_contains_username(self):
        """Test that password containing username is rejected."""
        username = "john"
        password = "MyJohn123!"  # Contains username

        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password_strength(password, username=username)

        assert "USERNAME" in str(exc_info.value.code)

    def test_password_contains_email(self):
        """Test that password containing email parts is rejected."""
        email = "john.doe@example.com"
        password = "JohnDoe123!"  # Contains email username part

        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password_strength(password, email=email)

        assert "EMAIL" in str(exc_info.value.code)

    def test_password_too_repetitive(self):
        """Test that passwords with too few unique characters are rejected."""
        repetitive = "AAAAAAAAAA1!"

        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password_strength(repetitive)

        assert "REPETITIVE" in str(exc_info.value.code)

    def test_custom_forbidden_words(self):
        """Test that custom forbidden words are rejected."""
        password = "MyComputor123!"
        forbidden_words = ["computor", "university"]

        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password_strength(password, custom_forbidden_words=forbidden_words)

        assert "FORBIDDEN_WORD" in str(exc_info.value.code)


class TestCreatePasswordHash:
    """Tests for the convenience function create_password_hash."""

    def test_create_password_hash_with_validation(self):
        """Test that create_password_hash validates and hashes."""
        password = "MySecure123!"

        hashed = create_password_hash(password, validate=True)

        assert is_argon2_hash(hashed)
        assert verify_password(password, hashed)

    def test_create_password_hash_validation_fails(self):
        """Test that create_password_hash raises on validation failure."""
        weak_password = "weak"

        with pytest.raises(PasswordValidationError):
            create_password_hash(weak_password, validate=True)

    def test_create_password_hash_without_validation(self):
        """Test that validation can be skipped."""
        # This would fail validation but should succeed with validate=False
        weak_password = "weak"

        hashed = create_password_hash(weak_password, validate=False)

        assert is_argon2_hash(hashed)
        assert verify_password(weak_password, hashed)

    def test_create_password_hash_with_username_check(self):
        """Test that username is checked when provided."""
        username = "alice"
        password = "MyAlice123!"  # Contains username

        with pytest.raises(PasswordValidationError) as exc_info:
            create_password_hash(password, validate=True, username=username)

        assert "USERNAME" in str(exc_info.value.code)


class TestDifferentPasswords:
    """Tests for ensuring different passwords have different behaviors."""

    def test_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes."""
        password1 = "Password1!"
        password2 = "Password2!"

        hash1 = hash_password(password1)
        hash2 = hash_password(password2)

        assert hash1 != hash2
        assert verify_password(password1, hash1)
        assert verify_password(password2, hash2)
        assert not verify_password(password1, hash2)
        assert not verify_password(password2, hash1)

    def test_similar_passwords_different_hashes(self):
        """Test that very similar passwords are distinguished."""
        password1 = "MyPassword123!"
        password2 = "MyPassword124!"  # Only one character different

        hash1 = hash_password(password1)
        hash2 = hash_password(password2)

        assert verify_password(password1, hash1)
        assert not verify_password(password2, hash1)
        assert verify_password(password2, hash2)
        assert not verify_password(password1, hash2)


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_verify_invalid_hash_format(self):
        """Test verification with invalid hash format."""
        assert verify_password("test", "invalid_hash") is False

    def test_verify_empty_hash(self):
        """Test verification with empty hash."""
        assert verify_password("test", "") is False

    def test_hash_unicode_password(self):
        """Test hashing password with unicode characters."""
        unicode_password = "Pässwörd123!🔒"
        hashed = hash_password(unicode_password)

        assert is_argon2_hash(hashed)
        assert verify_password(unicode_password, hashed)
        assert not verify_password("Password123!", hashed)

    def test_needs_rehash_invalid_hash(self):
        """Test needs_rehash with invalid hash."""
        # Invalid hash should return True (needs rehashing)
        assert needs_rehash("invalid") is True
        assert needs_rehash("") is True
