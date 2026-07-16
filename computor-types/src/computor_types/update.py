"""
Self-update DTOs.

Pydantic models for the System -> Updates admin page: running/remote version
comparison and the state of a triggered self-update run.
"""

from typing import Optional

from pydantic import BaseModel, Field


class SystemUpdateState(BaseModel):
    """State of the last (or currently running) self-update run."""
    status: str = Field(
        default="idle",
        description="idle | requested | running | success | failed | rolled_back",
    )
    phase: str = Field(
        default="",
        description=(
            "Progress within a run: preflight | checking | checking_out | building | "
            "entering_maintenance | starting | health_check | finalizing | rolling_back"
        ),
    )
    message: str = ""
    from_commit: Optional[str] = None
    to_commit: Optional[str] = None
    requested_by: Optional[str] = None
    requested_by_name: Optional[str] = None
    requested_at: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    error: Optional[str] = None


class SystemUpdateStatusGet(BaseModel):
    """Running vs. remote version, updater availability, and last run state."""
    update_enabled: bool = False
    running_commit: str = "unknown"
    running_branch: str = "unknown"
    repo_url: str = Field(
        default="",
        description="Configured deployment repo URL (credentials stripped).",
    )
    tracked_branch: str = ""
    remote_commit: Optional[str] = None
    remote_checked_at: Optional[str] = None
    remote_error: Optional[str] = None
    update_available: bool = False
    updater_online: bool = Field(
        default=False,
        description="Whether the updater sidecar heartbeat is live (always false in dev).",
    )
    state: SystemUpdateState = Field(default_factory=SystemUpdateState)


class SystemUpdateTriggerResponse(BaseModel):
    """Response to a successfully queued update request."""
    status: str = "requested"
    requested_at: str
