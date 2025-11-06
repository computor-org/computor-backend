"""
DTOs for lecturer deployment operations.

These DTOs support the lecturer workflow for assigning examples to course contents
before system-level release to Git repositories.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class AssignExampleRequest(BaseModel):
    """Request to assign an example to a course content (assignment)."""
    example_id: Optional[str] = Field(None, description="ID of the example to assign (UUID)")
    example_identifier: Optional[str] = Field(None, description="Identifier path of the example (e.g., 'itpcp.pgph.mat.function_time_formatter')")
    version_tag: str = Field(
        description="Specific version tag using semantic versioning (e.g., '1.0.0', '2.1.3-beta')"
    )

    def model_post_init(self, __context):
        """Validate that either example_id or example_identifier is provided."""
        if not self.example_id and not self.example_identifier:
            raise ValueError("Either example_id or example_identifier must be provided")
        if self.example_id and self.example_identifier:
            raise ValueError("Provide either example_id or example_identifier, not both")


class AssignExampleResponse(BaseModel):
    """Response after assigning an example."""
    deployment_id: str = Field(description="ID of the deployment record")
    course_content_id: str
    example_id: str
    example_version_id: str
    version_tag: str
    deployment_status: str = Field(description="Status: 'pending'")
    assigned_at: datetime
    message: str = Field(description="Success message")


class DeploymentGet(BaseModel):
    """Detailed deployment information for a course content."""
    id: str
    course_content_id: str
    example_id: Optional[str] = None
    example_version_id: Optional[str] = None
    example_identifier: Optional[str] = None
    version_tag: Optional[str] = None
    deployment_status: str
    deployment_message: Optional[str] = None
    assigned_at: datetime
    deployed_at: Optional[datetime] = None
    deployment_path: Optional[str] = None

    # Enriched data from joins
    example_title: Optional[str] = None
    example_directory: Optional[str] = None
    example_description: Optional[str] = None
    course_content_title: Optional[str] = None
    course_content_path: Optional[str] = None


class DeploymentList(BaseModel):
    """Minimal deployment info for list views."""
    id: str
    course_content_id: str
    deployment_status: str
    version_tag: Optional[str] = None
    assigned_at: datetime
    deployed_at: Optional[datetime] = None


class UnassignExampleResponse(BaseModel):
    """Response after unassigning an example."""
    course_content_id: str
    message: str = Field(description="Success message")
    previous_example_id: Optional[str] = None
    previous_version_tag: Optional[str] = None


class ValidationError(BaseModel):
    """Single validation error for release validation."""
    course_content_id: str
    title: str
    path: str
    issue: str


class ReleaseValidationError(BaseModel):
    """Error response when release validation fails."""
    error: str = Field(description="Main error message")
    validation_errors: list[ValidationError] = Field(description="List of specific issues")
    total_issues: int = Field(description="Count of validation errors")
