"""DTOs for lecturer GitLab permission sync operations."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class GitLabSyncRequest(BaseModel):
    """Request to sync GitLab permissions for a course member."""
    force: bool = Field(
        default=False,
        description="Force sync even if recently synced"
    )


class GitLabSyncResult(BaseModel):
    """Result of GitLab permission sync operation."""
    course_member_id: str
    user_id: str
    username: str
    course_role_id: str
    sync_status: str  # "success", "failed", "skipped"
    message: Optional[str] = None
    permissions_granted: List[str] = Field(default_factory=list)
    permissions_updated: List[str] = Field(default_factory=list)
    api_calls_made: int = 0
    synced_at: Optional[datetime] = None
