"""
Custom Ltree implementation that allows hyphens in path segments.

This extends sqlalchemy-utils Ltree to match PostgreSQL's actual ltree specification
which allows A-Za-z0-9_- characters in path segments.
"""

import re
from sqlalchemy_utils.primitives.ltree import Ltree as BaseLtree
from sqlalchemy_utils.types.ltree import LtreeType as BaseLtreeType
from sqlalchemy_utils.utils import str_coercible

# Updated regex pattern that includes hyphens (matches PostgreSQL ltree spec)
path_matcher = re.compile(r'^[A-Za-z0-9_-]+(\.[A-Za-z0-9_-]+)*$')


@str_coercible
class Ltree(BaseLtree):
    """
    Custom Ltree class that allows hyphens in path segments.
    
    This matches PostgreSQL's actual ltree specification:
    https://www.postgresql.org/docs/current/ltree.html
    
    Valid characters: A-Za-z0-9_-
    """
    
    @classmethod
    def validate(cls, path):
        """Validate ltree path with hyphen support."""
        if path_matcher.match(path) is None:
            raise ValueError(
                f"'{path}' is not a valid ltree path. "
                f"Path segments must contain only letters, numbers, underscores, and hyphens."
            )


class LtreeType(BaseLtreeType):
    """
    Custom LtreeType that uses our hyphen-supporting Ltree class.
    """
    
    # Set cache_ok to True to enable SQLAlchemy caching and remove warnings
    cache_ok = True
    
    def _coerce(self, value):
        """Override to use our custom Ltree class."""
        if value:
            return Ltree(value)