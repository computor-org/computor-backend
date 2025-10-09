"""Pydantic DTOs for tutor grading operations on submission artifacts."""
from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
from computor_types.grading import GradingStatus
from computor_types.student_course_contents import CourseContentStudentList

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
    status: Optional[GradingStatus] = Field(None, description="Grading status")
    feedback: Optional[str] = Field(None, description="Feedback/comment for the student")

class GradedArtifactInfo(BaseModel):
    """Information about the artifact that was graded.

    This provides context about which specific artifact received the grade,
    useful for tracking grading history and artifact metadata.
    """
    id: str = Field(..., description="The artifact ID that was graded")
    created_at: Optional[str] = Field(None, description="When the artifact was created (ISO format)")
    properties: Optional[dict[str, Any]] = Field(None, description="Additional artifact properties (e.g., GitLab info)")

class TutorGradeResponse(CourseContentStudentList):
    """Response after creating a grade through the tutor endpoint.

    Returns the updated course content information with the new grade applied.
    We extend CourseContentStudentList to maintain backward compatibility.
    """
    # Additional field to indicate which artifact was graded
    graded_artifact_id: Optional[str] = None
    graded_artifact_info: Optional[GradedArtifactInfo] = None