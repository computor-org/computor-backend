"""DTOs for the git server registry (admin / _organization_manager managed).

The registry holds the git server instances Computor knows about (our Forgejo,
external GitLabs). ``managed`` instances carry a service ``token`` used for
backend-babysat student-repo provisioning. The token is write-only — it is
stored encrypted and NEVER returned (``GitServerGet`` exposes only ``has_token``).
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

GitServerType = Literal['forgejo', 'gitlab']


class GitServerCreate(BaseModel):
    type: GitServerType
    base_url: str = Field(..., min_length=1, description="Base URL of the git server instance")
    name: Optional[str] = Field(None, description="Human-readable label")
    managed: bool = Field(False, description="True if Computor operates this instance and holds a service token")
    token: Optional[str] = Field(None, description="Service token; stored encrypted, never returned")


class GitServerUpdate(BaseModel):
    name: Optional[str] = None
    managed: Optional[bool] = None
    # Provide a new token to replace it; provide "" to clear it; omit to keep.
    token: Optional[str] = Field(None, description="Replacement service token (\"\" clears, omit keeps)")


class GitServerGet(BaseModel):
    id: str
    type: str
    base_url: str
    name: Optional[str] = None
    managed: bool
    has_token: bool = Field(..., description="Whether a service token is stored (the token itself is never returned)")
    created_at: Optional[datetime] = None
