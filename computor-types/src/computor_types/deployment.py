"""
Pydantic interfaces for deployment tracking.

This module contains DTOs for the deployment system that tracks
example assignments to course content.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator

from computor_types.example import ExampleVersionList

from .base import BaseEntityGet

if TYPE_CHECKING:
    from .example import ExampleVersionGet

# Deployment DTOs

class CourseContentDeploymentGet(BaseEntityGet):
    """Get deployment details."""
    id: str
    course_content_id: str
    example_version_id: Optional[str]
    # Source identity (works even without DB Example)
    example_identifier: Optional[str] = None
    version_tag: Optional[str] = None
    deployment_status: str
    deployment_message: Optional[str] = None
    assigned_at: datetime
    deployed_at: Optional[datetime] = None
    last_attempt_at: Optional[datetime] = None
    deployment_path: Optional[str] = None
    version_identifier: Optional[str] = None
    deployment_metadata: Optional[Dict[str, Any]] = None
    workflow_id: Optional[str] = None  # Current/last Temporal workflow ID

    # Relationships (optionally loaded)
    example_version: Optional['ExampleVersionGet'] = None

    model_config = ConfigDict(from_attributes=True)

    @staticmethod
    def _cast_ltree(value):
        try:
            return str(value) if value is not None else None
        except Exception:
            return value

    @field_validator('example_identifier', mode='before')
    @classmethod
    def cast_source_identifier(cls, v):
        return cls._cast_ltree(v)

class CourseContentDeploymentList(BaseModel):
    """List view of deployments."""
    id: str
    course_content_id: str
    example_version_id: Optional[str]
    example_identifier: Optional[str] = None
    version_tag: Optional[str] = None
    deployment_status: str
    assigned_at: datetime
    deployed_at: Optional[datetime]
    version_identifier: Optional[str]
    has_newer_version: bool = False

    example_version: Optional['ExampleVersionList'] = None

    model_config = ConfigDict(from_attributes=True)

    @staticmethod
    def _cast_ltree(value):
        try:
            return str(value) if value is not None else None
        except Exception:
            return value

    @field_validator('example_identifier', mode='before')
    @classmethod
    def cast_source_identifier(cls, v):
        return cls._cast_ltree(v)

# Deployment History DTOs

class DeploymentHistoryGet(BaseModel):
    """Get deployment history entry."""
    id: str
    deployment_id: str
    action: str
    example_version_id: Optional[str]
    previous_example_version_id: Optional[str]
    example_identifier: Optional[str] = None
    version_tag: Optional[str] = None
    workflow_id: Optional[str]
    created_at: datetime
    created_by: Optional[str]

    # Relationships
    example_version: Optional['ExampleVersionGet'] = None
    previous_example_version: Optional['ExampleVersionGet'] = None

    model_config = ConfigDict(from_attributes=True)

# Aggregate DTOs for API responses

class DeploymentWithHistory(BaseModel):
    """Deployment with its full history."""
    deployment: CourseContentDeploymentGet
    history: List[DeploymentHistoryGet]

    model_config = ConfigDict(from_attributes=True)

class DeploymentSummary(BaseModel):
    """Summary of deployments for a course."""
    course_id: str
    total_content: int = Field(description="Total course content items")
    submittable_content: int = Field(description="Total submittable content (assignments)")
    deployments_total: int = Field(description="Total deployments")
    deployments_pending: int = Field(description="Deployments pending")
    deployments_deployed: int = Field(description="Successfully deployed")
    deployments_failed: int = Field(description="Failed deployments")
    last_deployment_at: Optional[datetime] = Field(None, description="Most recent deployment")

    model_config = ConfigDict(from_attributes=True)
