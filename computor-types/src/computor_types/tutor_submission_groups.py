"""DTOs for tutor submission group endpoints."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class TutorSubmissionGroupMember(BaseModel):
    """Member information in a submission group."""
    id: str
    course_member_id: str
    user_id: str
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    email: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TutorSubmissionGroupList(BaseModel):
    """List view of submission groups for tutors."""
    id: str
    course_id: str
    course_content_id: str
    display_name: str  # Computed: "FirstName LastName" for individuals, "Team: ..." for groups
    max_group_size: int
    max_submissions: Optional[int] = None
    max_test_runs: Optional[int] = None

    # Aggregated information
    member_count: int = 0
    submission_count: int = 0
    latest_submission_at: Optional[datetime] = None
    has_ungraded_submissions: bool = False

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TutorSubmissionGroupGet(BaseModel):
    """Detailed view of a submission group for tutors."""
    id: str
    course_id: str
    course_content_id: str
    display_name: str  # Computed: "FirstName LastName" for individuals, "Team: ..." for groups
    max_group_size: int
    max_submissions: Optional[int] = None
    max_test_runs: Optional[int] = None
    properties: Optional[dict] = None

    # Members
    members: List[TutorSubmissionGroupMember] = []
    member_count: int = 0

    # Submission statistics
    submission_count: int = 0
    test_run_count: int = 0
    latest_submission_at: Optional[datetime] = None
    latest_submission_id: Optional[str] = None
    has_ungraded_submissions: bool = False

    # Grading statistics
    graded_submission_count: int = 0
    latest_grade: Optional[float] = None
    average_grade: Optional[float] = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TutorSubmissionGroupQuery(BaseModel):
    """Query parameters for filtering submission groups."""
    course_id: Optional[str] = None
    course_content_id: Optional[str] = None
    course_group_id: Optional[str] = None
    has_submissions: Optional[bool] = None
    has_ungraded_submissions: Optional[bool] = None
    limit: int = 100
    offset: int = 0
