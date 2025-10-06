"""Computor CLI - Command-line interface for Computor platform."""

__version__ = "0.1.0"

# Minimal exports - most commands still depend on computor_backend
# and will be fully migrated in Phase 4
from .cli import cli

__all__ = ["cli"]