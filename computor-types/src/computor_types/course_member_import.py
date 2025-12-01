"""DTOs for course member bulk import functionality."""
from enum import Enum
from typing import List, Optional, TYPE_CHECKING
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from computor_types.course_members import CourseMemberGet
    from computor_types.course_groups import CourseGroupGet


class ImportStatus(str, Enum):
    """Status of an individual import record."""
    SUCCESS = "success"
    ERROR = "error"
    SKIPPED = "skipped"
    UPDATED = "updated"


class CourseMemberImportRow(BaseModel):
    """Represents a single row from the import file."""
    email: str = Field(..., description="Email address (required, used as identifier)")
    given_name: Optional[str] = Field(None, description="First name (Vorname)")
    family_name: Optional[str] = Field(None, description="Last name (Familienname)")
    student_id: Optional[str] = Field(None, description="Student ID (Matrikelnummer)")
    course_group_title: Optional[str] = Field(None, description="Course group title (Gruppe)")
    course_role_id: str = Field("_student", description="Course role ID (default: _student)")

    # Additional optional fields from the XML
    incoming: Optional[str] = Field(None, description="Incoming student indicator")
    study_id: Optional[str] = Field(None, description="Study program ID (Kennzahl)")
    study_name: Optional[str] = Field(None, description="Study program name (Studium)")
    semester: Optional[int] = Field(None, description="Semester in study program")
    registration_date: Optional[str] = Field(None, description="Registration date")
    notes: Optional[str] = Field(None, description="Additional notes (Anmerkung)")


class CourseMemberImportResult(BaseModel):
    """Result of importing a single member."""
    row_number: int = Field(..., description="Row number in the import file")
    status: ImportStatus = Field(..., description="Import status")
    email: str = Field(..., description="Email from the import")
    user_id: Optional[str] = Field(None, description="User ID if created/found")
    course_member_id: Optional[str] = Field(None, description="Course member ID if created/updated")
    message: Optional[str] = Field(None, description="Success or error message")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings")


class CourseMemberImportRequest(BaseModel):
    """Request for bulk course member import."""
    course_id: str = Field(..., description="Course ID to import members into")
    members: List[CourseMemberImportRow] = Field(..., description="List of members to import")
    default_course_role_id: str = Field("_student", description="Default role for imported members")
    update_existing: bool = Field(False, description="Update existing users if found")
    create_missing_groups: bool = Field(True, description="Auto-create missing course groups")
    username_strategy: str = Field(
        "name",
        description="Username generation strategy: 'name' (from given/family name) or 'email' (from email prefix)"
    )
    batch_size: int = Field(
        5,
        description="Number of members to process per batch for GitLab operations (to avoid rate limits)"
    )
    batch_delay_seconds: int = Field(
        10,
        description="Delay in seconds between batches to respect GitLab API rate limits"
    )


class CourseMemberImportResponse(BaseModel):
    """Response from bulk course member import."""
    total: int = Field(..., description="Total number of records processed")
    success: int = Field(..., description="Number of successful imports")
    errors: int = Field(..., description="Number of errors")
    skipped: int = Field(..., description="Number of skipped records")
    updated: int = Field(..., description="Number of updated records")
    results: List[CourseMemberImportResult] = Field(..., description="Detailed results for each record")
    missing_groups: List[str] = Field(default_factory=list, description="Groups that were created automatically")


class CourseMemberImportPreview(BaseModel):
    """Preview of import without executing it."""
    valid_records: int = Field(..., description="Number of valid records")
    invalid_records: int = Field(..., description="Number of invalid records")
    new_users: int = Field(..., description="Estimated new users to create")
    existing_users: int = Field(..., description="Estimated existing users to update")
    issues: List[str] = Field(default_factory=list, description="Validation issues found")
    sample_records: List[CourseMemberImportRow] = Field(..., description="Sample of parsed records")


class SingleCourseMemberImportRequest(BaseModel):
    """Request for importing a single course member."""
    email: str = Field(..., description="Email address (required)")
    given_name: Optional[str] = Field(None, description="First name")
    family_name: Optional[str] = Field(None, description="Last name")
    course_group_title: Optional[str] = Field(None, description="Course group name")
    course_role_id: str = Field("_student", description="Course role ID (e.g., _student)")
    create_missing_group: bool = Field(True, description="Auto-create missing course group")


class SingleCourseMemberImportResponse(BaseModel):
    """Response from single course member import."""
    success: bool = Field(..., description="Whether the import was successful")
    message: Optional[str] = Field(None, description="Success or error message")
    course_member: Optional[dict] = Field(None, description="Created/updated course member")
    created_group: Optional[dict] = Field(None, description="Created course group if new")
