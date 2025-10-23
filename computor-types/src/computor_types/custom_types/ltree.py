"""
Pure Pydantic Ltree implementation for hierarchical paths.

This is a lightweight implementation for the types package that doesn't depend on SQLAlchemy.
It provides string validation and path manipulation for PostgreSQL ltree-style hierarchical paths.
"""

import re
from typing import Any, List
from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema


# Regex pattern that includes hyphens (matches PostgreSQL ltree spec)
# Valid characters: A-Za-z0-9_-
PATH_PATTERN = re.compile(r'^[A-Za-z0-9_-]+(\.[A-Za-z0-9_-]+)*$')


class Ltree(str):
    """
    Hierarchical path string for PostgreSQL ltree format.

    This matches PostgreSQL's ltree specification:
    https://www.postgresql.org/docs/current/ltree.html

    Valid characters in path segments: A-Za-z0-9_-
    Path segments are separated by dots (.)

    Examples:
        'organization'
        'organization.course-family'
        'org.course_family.course'
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        source_type: Any,
        handler: GetCoreSchemaHandler,
    ) -> core_schema.CoreSchema:
        """Define how Pydantic should validate this type."""
        return core_schema.with_info_after_validator_function(
            cls._validate,
            core_schema.str_schema(),
        )

    @classmethod
    def _validate(cls, value: str, _info: Any) -> 'Ltree':
        """Validate and create an Ltree instance."""
        if not isinstance(value, str):
            raise ValueError(f"Ltree must be a string, got {type(value)}")

        if not value:
            raise ValueError("Ltree path cannot be empty")

        if not PATH_PATTERN.match(value):
            raise ValueError(
                f"'{value}' is not a valid ltree path. "
                f"Path segments must contain only letters, numbers, underscores, and hyphens, "
                f"separated by dots (e.g., 'org.family.course')"
            )

        return cls(value)

    @property
    def path(self) -> List[str]:
        """Get path segments as a list."""
        return str(self).split('.')

    @property
    def depth(self) -> int:
        """Get the depth/level of the path."""
        return len(self.path)

    def parent(self) -> 'Ltree | None':
        """Get the parent path, or None if at root level."""
        segments = self.path
        if len(segments) <= 1:
            return None
        return Ltree('.'.join(segments[:-1]))

    def child(self, segment: str) -> 'Ltree':
        """Create a child path by appending a segment."""
        if not re.match(r'^[A-Za-z0-9_-]+$', segment):
            raise ValueError(
                f"'{segment}' is not a valid path segment. "
                f"Must contain only letters, numbers, underscores, and hyphens."
            )
        return Ltree(f"{self}.{segment}")

    def is_ancestor_of(self, other: 'Ltree') -> bool:
        """Check if this path is an ancestor of another path."""
        if not isinstance(other, (str, Ltree)):
            return False
        other_str = str(other)
        self_str = str(self)
        return other_str.startswith(self_str + '.')

    def is_descendant_of(self, other: 'Ltree') -> bool:
        """Check if this path is a descendant of another path."""
        if not isinstance(other, (str, Ltree)):
            return False
        return Ltree(other).is_ancestor_of(self)


# For backwards compatibility - LtreeType is used in the backend
# In the types package, we just need the Ltree class itself
LtreeType = Ltree
