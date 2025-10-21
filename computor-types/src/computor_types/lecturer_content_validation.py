"""
Pydantic DTOs for batch content validation in lecturer API.

This provides an optimized batch validation endpoint to reduce
100+ HTTP requests to a single request when validating multiple
course contents with their assigned examples and versions.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List

from .base import EntityInterface


class ContentValidationItem(BaseModel):
    """Single content item to validate."""
    content_id: str = Field(description="UUID of course content")
    example_identifier: str = Field(description="Example identifier/slug from meta.yaml (dot-separated ltree path)")
    version_tag: str = Field(description="Version tag from meta.yaml (e.g., '1.0.0')")

    model_config = ConfigDict(from_attributes=True)


class ExampleValidationResult(BaseModel):
    """Validation result for example existence."""
    identifier: str = Field(description="Example identifier that was checked")
    exists: bool = Field(description="Whether the example exists")
    example_id: Optional[str] = Field(None, description="Example ID if exists")
    message: Optional[str] = Field(None, description="Error message if not exists")

    model_config = ConfigDict(from_attributes=True)


class VersionValidationResult(BaseModel):
    """Validation result for version existence."""
    version_tag: str = Field(description="Version tag that was checked")
    exists: bool = Field(description="Whether the version exists")
    version_id: Optional[str] = Field(None, description="Version ID if exists")
    message: Optional[str] = Field(None, description="Error message if not exists")

    model_config = ConfigDict(from_attributes=True)


class ContentValidationResult(BaseModel):
    """Validation result for a single content item."""
    content_id: str
    valid: bool = Field(description="Whether this content is valid overall")
    example_validation: ExampleValidationResult
    version_validation: VersionValidationResult
    validation_message: Optional[str] = Field(
        None,
        description="Overall validation message for this content"
    )

    model_config = ConfigDict(from_attributes=True)


class ContentValidationCreate(BaseModel):
    """Request to validate multiple course contents - batch validation."""
    content_validations: List[ContentValidationItem] = Field(
        description="List of course content to validate"
    )

    model_config = ConfigDict(from_attributes=True)


class ContentValidationGet(BaseModel):
    """Response from batch validation."""
    valid: bool = Field(description="Overall validation status")
    total_validated: int = Field(description="Total items validated")
    total_issues: int = Field(description="Number of issues found")
    validation_results: List[ContentValidationResult] = Field(
        description="Validation results for each content item"
    )

    model_config = ConfigDict(from_attributes=True)


# EntityInterface for consistency with codebase patterns
class ContentValidationInterface(EntityInterface):
    """Interface for batch content validation."""
    create = ContentValidationCreate  # POST request body
    get = ContentValidationGet        # Response
