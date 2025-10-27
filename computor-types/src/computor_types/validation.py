"""
Validation utilities and schemas for the Computor platform.
"""

import re
from pydantic import BaseModel, Field


class SemanticVersion(BaseModel):
    """
    Semantic version following semver.org spec (subset).

    Supports format: <major>.<minor>.<patch>[-<prerelease>]

    Examples:
        - 1.0.0
        - 2.1.3
        - 1.0.0-alpha
        - 3.2.1-beta.2
    """
    major: int = Field(ge=0, description="Major version number")
    minor: int = Field(ge=0, description="Minor version number")
    patch: int = Field(ge=0, description="Patch version number")
    prerelease: str | None = Field(None, description="Optional prerelease identifier")

    @classmethod
    def from_string(cls, version_str: str) -> "SemanticVersion":
        """
        Parse semantic version from string.

        Args:
            version_str: Version string to parse

        Returns:
            SemanticVersion instance

        Raises:
            ValueError: If version string format is invalid
        """
        pattern = r'^(\d+)\.(\d+)\.(\d+)(-[a-zA-Z0-9.-]+)?$'
        match = re.match(pattern, version_str)
        if not match:
            raise ValueError(
                f"Invalid version format: '{version_str}'. "
                "Expected format: <major>.<minor>.<patch>[-<prerelease>] "
                "(e.g., '1.0.0' or '2.1.3-alpha')"
            )

        major, minor, patch, prerelease = match.groups()
        return cls(
            major=int(major),
            minor=int(minor),
            patch=int(patch),
            prerelease=prerelease[1:] if prerelease else None  # Remove leading '-'
        )

    def __str__(self) -> str:
        """Return string representation of version."""
        base = f"{self.major}.{self.minor}.{self.patch}"
        return f"{base}-{self.prerelease}" if self.prerelease else base

    def __repr__(self) -> str:
        """Return detailed representation of version."""
        return f"SemanticVersion('{str(self)}')"


def normalize_version(version_str: str) -> str:
    """
    Normalize a version string to semantic versioning format.

    Converts short versions to full semver format:
    - '1' -> '1.0.0'
    - '1.0' -> '1.0.0'
    - '1.0.0' -> '1.0.0' (unchanged)
    - '2.1.3-alpha' -> '2.1.3-alpha' (unchanged)

    Args:
        version_str: Version string to normalize

    Returns:
        Normalized version string in semver format
    """
    if not version_str:
        return '1.0.0'

    version_str = version_str.strip()

    # Check if it has a prerelease suffix (e.g., '1.0.0-alpha')
    prerelease = None
    if '-' in version_str:
        version_part, prerelease = version_str.split('-', 1)
    else:
        version_part = version_str

    # Split version into components
    parts = version_part.split('.')

    # Pad with zeros to get exactly 3 parts
    while len(parts) < 3:
        parts.append('0')

    # Validate that all parts are numeric
    try:
        parts = [str(int(p)) for p in parts[:3]]  # Take only first 3 parts
    except ValueError:
        # If conversion fails, return original string (will fail validation later)
        return version_str

    # Reconstruct normalized version
    normalized = '.'.join(parts)
    if prerelease:
        normalized = f"{normalized}-{prerelease}"

    return normalized


def validate_version_format(version_str: str) -> bool:
    """
    Validate that a version string follows semantic versioning.

    Args:
        version_str: Version string to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        SemanticVersion.from_string(version_str)
        return True
    except ValueError:
        return False
