"""DTOs for course member import functionality."""
from typing import List, Optional
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
    workflow_id: Optional[str] = Field(None, description="Workflow ID for repository creation task (use GET /tasks/{workflow_id}/status to check progress)")


class CourseMemberImportRow(BaseModel):
    """A single member parsed from an uploaded file (preview before import)."""
    email: str = Field(..., description="Email address")
    given_name: Optional[str] = Field(None, description="First name")
    family_name: Optional[str] = Field(None, description="Last name")
    student_id: Optional[str] = Field(None, description="Matriculation / student number")
    course_group_title: Optional[str] = Field(None, description="Course group name")
    course_role_id: Optional[str] = Field(None, description="Course role ID (e.g., _student)")
    incoming: Optional[str] = Field(None, description="Incoming/exchange marker")
    study_id: Optional[str] = Field(None, description="Study programme id")
    study_name: Optional[str] = Field(None, description="Study programme name")
    semester: Optional[int] = Field(None, description="Semester in study")
    registration_date: Optional[str] = Field(None, description="Registration date")
    notes: Optional[str] = Field(None, description="Free-text notes")


class CourseMemberImportFileParseRequest(BaseModel):
    """Upload payload for the file parser: the file as base64 (handles binary
    xlsx as well as text csv/json/xml over plain JSON)."""
    filename: str = Field(..., description="Original filename — used to detect the format")
    content_base64: str = Field(..., description="Base64-encoded file bytes")


class CourseMemberImportParseResponse(BaseModel):
    """Rows parsed from an uploaded member file. No database writes occur."""
    rows: List[CourseMemberImportRow] = Field(default_factory=list, description="Parsed members (rows without an email are dropped)")
    detected_format: Optional[str] = Field(None, description="csv | json | xlsx | xml")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal parse warnings")
