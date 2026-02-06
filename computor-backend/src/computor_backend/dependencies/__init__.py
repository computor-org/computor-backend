"""
FastAPI dependencies for computor-backend.

This package contains reusable FastAPI dependencies that can be
injected into routers and endpoints.
"""

from .plugin import get_current_user, mint_workspace_token

__all__ = [
    "get_current_user",
    "mint_workspace_token",
]
