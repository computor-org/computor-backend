"""DTOs for lecturer GitLab permission sync operations."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class GitLabSyncRequest(BaseModel):
    """Request to sync GitLab permissions for a course member."""
    access_token: Optional[str] = Field(
        default=None,
        description="GitLab access token to check existing permissions before syncing (reduces API calls with organization token)"
    )


class GitLabSyncResult(BaseModel):
    """Result of GitLab permission sync operation."""
    course_member_id: str
    sync_status: str  # "success", "failed", "skipped"
    message: Optional[str] = None
