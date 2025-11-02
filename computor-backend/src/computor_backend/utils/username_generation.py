"""
Username generation utilities with name-based algorithm and collision handling.

This module provides intelligent username generation from given and family names,
with progressive expansion for collision handling and international character support.

Examples:
    - "Max Mustermann" → "mmusterm"
    - On collision: "mmusterm" → "mamusterm" → "maxmusterm"
    - International: "Müller" → "muller", "José García" → "jgarcia"
"""

from typing import Optional
from sqlalchemy.orm import Session
from text_unidecode import unidecode
import logging

from computor_backend.model.auth import User

logger = logging.getLogger(__name__)


def normalize_name_for_username(name: str) -> str:
    """
    Normalize a name for use in usernames.

    Converts international characters to ASCII equivalents and removes
    non-alphanumeric characters.

    Args:
        name: Name to normalize (e.g., "Müller", "José")

    Returns:
        Normalized name (e.g., "muller", "jose")

    Examples:
        >>> normalize_name_for_username("Müller")
        'muller'
        >>> normalize_name_for_username("José García")
        'jose garcia'
        >>> normalize_name_for_username("O'Brien")
        'obrien'
    """
    if not name:
        return ""

    # Convert to lowercase and decode international characters
    name = name.lower()
    name = unidecode(name)

    # Keep only alphanumeric characters and spaces
    normalized = ''.join(c if c.isalnum() or c.isspace() else '' for c in name)

    return normalized.strip()


def generate_username_from_names(
    given_name: Optional[str],
    family_name: Optional[str],
    db: Session,
    target_length: int = 8
) -> str:
    """
    Generate a unique username from given and family names.

    Algorithm:
    1. Start with first initial + truncated family name (e.g., "Max Mustermann" → "mmusterm")
    2. On collision, progressively use more chars from given name:
       - "mmusterm" exists → "mamusterm"
       - "mamusterm" exists → "maxmusterm"
    3. If all given name chars used, add numeric suffix

    Args:
        given_name: First name (can be None)
        family_name: Last name (can be None)
        db: Database session for uniqueness checking
        target_length: Target username length (default: 8)

    Returns:
        Unique username

    Examples:
        >>> generate_username_from_names("Max", "Mustermann", db, target_length=8)
        'mmusterm'
        >>> generate_username_from_names("Müller", "José", db, target_length=8)
        'jmuller'
        >>> generate_username_from_names(None, "Smith", db, target_length=8)
        'smith'
    """
    # Normalize names
    given = normalize_name_for_username(given_name or "")
    family = normalize_name_for_username(family_name or "")

    # Remove spaces from normalized names
    given = given.replace(" ", "")
    family = family.replace(" ", "")

    # Edge case: No names provided
    if not given and not family:
        logger.warning("No names provided for username generation, using 'user' as base")
        return _ensure_username_unique("user", db)

    # Edge case: Only family name
    if not given:
        base_username = family[:target_length]
        return _ensure_username_unique(base_username, db)

    # Edge case: Only given name
    if not family:
        base_username = given[:target_length]
        return _ensure_username_unique(base_username, db)

    # Standard algorithm: first_initial + family_truncated
    # Progressive expansion strategy for collisions

    # Start with 1 char from given name
    for given_chars in range(1, len(given) + 1):
        # Calculate remaining space for family name
        family_chars = target_length - given_chars

        if family_chars < 1:
            # Not enough space, use all chars and let it be longer
            family_chars = len(family)

        # Build username
        username = given[:given_chars] + family[:family_chars]

        # Check if unique
        if not db.query(User).filter(User.username == username).first():
            logger.info(f"Generated username '{username}' from names (given={given_name}, family={family_name})")
            return username

    # All given name chars used, still collision
    # Use full given name + full family name, then add numeric suffix
    base_username = given + family
    logger.warning(f"All expansion attempts failed for names (given={given_name}, family={family_name}), using numeric suffix")
    return _ensure_username_unique(base_username, db)


def _ensure_username_unique(base_username: str, db: Session) -> str:
    """
    Ensure username is unique by adding numeric suffix if needed.

    Args:
        base_username: Base username to check
        db: Database session

    Returns:
        Unique username (with numeric suffix if needed)

    Examples:
        >>> _ensure_username_unique("mmusterm", db)
        'mmusterm'  # If unique
        >>> _ensure_username_unique("jsmith", db)
        'jsmith1'   # If 'jsmith' exists
        >>> _ensure_username_unique("jsmith", db)
        'jsmith2'   # If 'jsmith' and 'jsmith1' exist
    """
    username = base_username
    counter = 1

    while db.query(User).filter(User.username == username).first():
        username = f"{base_username}{counter}"
        counter += 1

        # Safety limit
        if counter > 9999:
            logger.error(f"Username generation failed after 9999 attempts for base '{base_username}'")
            raise ValueError(f"Could not generate unique username for base '{base_username}'")

    return username
