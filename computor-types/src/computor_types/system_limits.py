"""Deployment-wide admission limits (#351).

Two limits an operator turns at runtime, served by ``GET/PUT /system/limits``:

- ``max_workspace_users`` — how many DISTINCT users may hold an active Coder
  workspace at once. A user refused here can still work locally in VS Code,
  which is why the refusal carries the extension's download URL.
- ``max_concurrent_logins`` — how many DISTINCT users may be signed in at once.

Both exempt staff (admins and the builtin manager/maintainer roles), and both
are separate from ``WorkspaceTemplateSettings.max_running_workspaces``, which
models a hard external constraint (MATLAB licence seats) and binds everyone.

``null`` means unlimited on both, matching the per-template quota.
"""

from typing import Optional

from pydantic import BaseModel, Field


class InstanceLimitsUsage(BaseModel):
    """What the limits currently measure, so an admin sees headroom not guesses."""

    workspace_users: int = Field(
        description="Distinct users holding a running or starting workspace right now.",
    )
    login_seats: int = Field(
        description="Distinct users holding a login seat — one per user however "
        "many tabs or devices they are signed in from.",
    )
    workspace_users_available: Optional[bool] = Field(
        None,
        description="False when the workspace-user count could not be read (Coder "
        "unreachable or disabled); the number above is then meaningless.",
    )


class InstanceLimitsGet(BaseModel):
    """The stored limits plus their current usage."""

    max_workspace_users: Optional[int] = Field(
        None,
        description="Max distinct users with an active workspace; null = unlimited, "
        "0 = no non-staff workspaces at all.",
    )
    max_concurrent_logins: Optional[int] = Field(
        None,
        description="Max distinct users signed in at once; null = unlimited, "
        "0 = no non-staff logins at all.",
    )
    login_idle_minutes: int = Field(
        description="How long a login seat is held after the user's last request.",
    )
    local_install_url: Optional[str] = Field(
        None,
        description="Download URL for the local VS Code extension, quoted in both "
        "refusals; null when EXTENSION_PUBLIC_DOWNLOAD_URL is unset.",
    )
    usage: Optional[InstanceLimitsUsage] = Field(
        None,
        description="Current usage of both limits.",
    )


class InstanceLimitsUpdate(BaseModel):
    """Full replacement of the stored limits (PUT semantics)."""

    max_workspace_users: Optional[int] = Field(
        None,
        ge=0,
        description="Max distinct users with an active workspace; null = unlimited.",
    )
    max_concurrent_logins: Optional[int] = Field(
        None,
        ge=0,
        description="Max distinct users signed in at once; null = unlimited.",
    )
    login_idle_minutes: int = Field(
        30,
        ge=1,
        description="Idle window for a login seat, in minutes. Keep it above 15: "
        "an active client re-authenticates (and so refreshes its seat) at most "
        "every 15 minutes, so a shorter window evicts users mid-session.",
    )
