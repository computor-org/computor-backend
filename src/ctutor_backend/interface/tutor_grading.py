"""Pydantic DTOs for tutor grading operations on submission artifacts."""
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from ctutor_backend.interface.grading import GradingStatus
from ctutor_backend.interface.student_course_contents import CourseContentStudentList


class TutorGradeCreate(BaseModel):
    """DTO for creating a grade through the tutor endpoint.

    This is used when a tutor grades a student's submission for a specific course content.
    The endpoint will automatically find the latest artifact for the submission group.
    """
    # Optional artifact_id - if provided, grades this specific artifact
    # If not provided, grades the latest artifact for the submission group
    artifact_id: Optional[str] = None

    # Grading information
    grade: Optional[float] = Field(None, ge=0.0, le=1.0, description="Grade between 0.0 and 1.0")
    status: Optional[str] = Field(
        None,
        description="Status: corrected, correction_necessary, improvement_possible, not_reviewed"
    )
    feedback: Optional[str] = Field(None, description="Feedback/comment for the student")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        """Validate status string."""
        if v is not None:
            valid_statuses = {
                "corrected",
                "correction_necessary",
                "correction_possible",  # Alias for improvement_possible
                "improvement_possible",
                "not_reviewed"
            }
            if v not in valid_statuses:
                raise ValueError(f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
        return v


class TutorGradeResponse(CourseContentStudentList):
    """Response after creating a grade through the tutor endpoint.

    Returns the updated course content information with the new grade applied.
    We extend CourseContentStudentList to maintain backward compatibility.
    """
    # Additional field to indicate which artifact was graded
    graded_artifact_id: Optional[str] = None
    graded_artifact_info: Optional[dict] = None  # Additional info about the graded artifact