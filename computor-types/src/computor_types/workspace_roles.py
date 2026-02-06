"""Schemas for workspace role management."""

from pydantic import BaseModel, Field


class WorkspaceRoleUser(BaseModel):
    """A user with their workspace roles."""
    user_id: str
    email: str | None
    username: str | None
    given_name: str | None
    family_name: str | None
    roles: list[str] = Field(default_factory=list)


class WorkspaceRoleAssign(BaseModel):
    """Request to assign a workspace role by email."""
    email: str
    role_id: str
