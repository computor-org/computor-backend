"""DTOs for team management (student team creation, joining, leaving)."""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class TeamMemberInfo(BaseModel):
    """Information about a team member (for display in team lists)."""
    course_member_id: str
    user_id: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TeamFormationRules(BaseModel):
    """Team formation rules resolved from Course and CourseContent."""
    mode: str = "self_organized"
    max_group_size: int
    min_group_size: int = 1
    formation_deadline: Optional[str] = None
    allow_student_group_creation: bool = True
    allow_student_join_groups: bool = True
    allow_student_leave_groups: bool = True
    auto_assign_unmatched: bool = False
    lock_teams_at_deadline: bool = True
    require_approval: bool = False


class TeamCreate(BaseModel):
    """Request to create a new team."""
    team_name: Optional[str] = Field(None, description="Optional team name (default: generated from members)")


class TeamResponse(BaseModel):
    """Response when team is created or retrieved."""
    id: str
    course_content_id: str
    course_id: str
    max_group_size: int
    status: str = "forming"  # forming | locked | archived
    created_by: str = "student"  # student | instructor | system
    join_code: Optional[str] = None
    members: List[TeamMemberInfo]
    member_count: int
    can_join: bool  # Can more members join?
    locked_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AvailableTeam(BaseModel):
    """Team available for joining (limited info for privacy)."""
    id: str
    member_count: int
    max_group_size: int
    join_code: Optional[str] = None
    requires_approval: bool
    status: str
    members: List[TeamMemberInfo]  # Only show names, not full details

    model_config = ConfigDict(from_attributes=True)


class JoinTeamRequest(BaseModel):
    """Request to join a team."""
    join_code: Optional[str] = Field(None, description="Optional join code for direct access")


class JoinTeamResponse(BaseModel):
    """Response when joining a team."""
    id: str
    status: str  # "joined" | "pending_approval"
    message: str


class LeaveTeamResponse(BaseModel):
    """Response when leaving a team."""
    success: bool
    message: str


class TeamLockRequest(BaseModel):
    """Request to lock a team (instructor only)."""
    reason: Optional[str] = Field(None, description="Optional reason for locking")


class TeamLockResponse(BaseModel):
    """Response when team is locked."""
    id: str
    locked_at: datetime
    message: str
