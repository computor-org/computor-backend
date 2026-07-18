"""Schemas for workspace role management and provisioning."""

from typing import Optional

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


class WorkspaceProvisionRequest(BaseModel):
    """Request to provision a workspace."""
    email: Optional[str] = Field(None, description="Target user email. If omitted, provisions for the current user.")
    template: Optional[str] = Field(None, description="Workspace template name. Validated against the templates available in Coder; omit for the server default.")
    workspace_name: Optional[str] = Field(None, description="Custom workspace name. Defaults to a name derived from the template.")
    home_mode: Optional[str] = Field(
        None,
        description="Home volume mode: 'shared' (per-user home volume) or 'scratch' "
                    "(throwaway per-workspace volume). Full provisioners only; "
                    "self-provisioning always uses the template default (shared).",
    )
