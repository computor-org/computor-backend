"""DTOs for course member import functionality."""
from typing import Optional
from pydantic import BaseModel, Field


class CourseMemberImportRequest(BaseModel):
    """Request for importing a course member."""
    email: str = Field(..., description="Email address (required)")
    given_name: Optional[str] = Field(None, description="First name")
    family_name: Optional[str] = Field(None, description="Last name")
    course_group_title: Optional[str] = Field(None, description="Course group name")
    course_role_id: str = Field("_student", description="Course role ID (e.g., _student)")
    create_missing_group: bool = Field(True, description="Auto-create missing course group")


class CourseMemberImportResponse(BaseModel):
    """Response from course member import."""
    success: bool = Field(..., description="Whether the import was successful")
    message: Optional[str] = Field(None, description="Success or error message")
    course_member: Optional[dict] = Field(None, description="Created/updated course member")
    created_group: Optional[dict] = Field(None, description="Created course group if new")
