"""Computor Utils - Shared utility functions for Computor platform."""

__version__ = "0.1.0"

from .vsix_utils import parse_vsix_metadata

__all__ = [
    "parse_vsix_metadata",
]
