"""
Pydantic DTOs for cascade deletion operations.

These models define request/response types for bulk deletion of:
- Organizations (and all descendant data)
- Course Families (and all descendant courses)
- Courses (and all course-specific data)
- Examples (by identifier prefix pattern)
"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ForceLevel(str, Enum):
    """Force level for example deletion when deployments exist."""
    NONE = "none"  # Block if any active deployments exist
    OLD = "old"  # Allow if course is archived or deployment is failed/unassigned
    ALL = "all"  # Delete even if actively deployed (requires confirmation)


class EntityDeleteCount(BaseModel):
    """Count of deleted entities by type."""
    courses: int = 0
    course_families: int = 0
    course_members: int = 0
    course_groups: int = 0
    course_content_types: int = 0
    course_contents: int = 0
    submission_groups: int = 0
    submission_group_members: int = 0
    submission_artifacts: int = 0
    submission_grades: int = 0
    submission_reviews: int = 0
    results: int = 0
    result_artifacts: int = 0
    course_content_deployments: int = 0
    deployment_histories: int = 0
    course_member_comments: int = 0
    messages: int = 0
    example_repositories: int = 0
    examples: int = 0
    example_versions: int = 0
    example_dependencies: int = 0
    student_profiles: int = 0


class CascadeDeletePreview(BaseModel):
    """Preview of what will be deleted in a cascade operation."""
    entity_type: str = Field(..., description="Type of root entity being deleted")
    entity_id: str = Field(..., description="ID of root entity being deleted")
    entity_name: str = Field(..., description="Name/identifier of root entity")
    child_counts: EntityDeleteCount = Field(
        default_factory=EntityDeleteCount,
        description="Count of child entities that will be deleted"
    )
    minio_paths: List[str] = Field(
        default_factory=list,
        description="MinIO storage paths that will be cleaned up"
    )


class CascadeDeleteResult(BaseModel):
    """Result of a cascade deletion operation."""
    dry_run: bool = Field(..., description="Whether this was a preview only")
    entity_type: str = Field(..., description="Type of root entity deleted")
    entity_id: str = Field(..., description="ID of root entity deleted")
    deleted_counts: EntityDeleteCount = Field(
        default_factory=EntityDeleteCount,
        description="Count of entities deleted by type"
    )
    minio_objects_deleted: int = Field(
        0, description="Number of MinIO objects deleted"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Errors encountered during deletion"
    )


class ExampleDeletePreview(BaseModel):
    """Preview of a single example that would be deleted."""
    example_id: str
    identifier: str
    title: str
    directory: str
    repository_id: str
    repository_name: str
    version_count: int = Field(..., description="Number of versions to delete")
    storage_paths: List[str] = Field(
        default_factory=list,
        description="MinIO storage paths for versions"
    )
    deployment_references: int = Field(
        0, description="Count of CourseContentDeployments referencing this example"
    )


class ExampleBulkDeleteRequest(BaseModel):
    """Request to delete examples by identifier prefix pattern."""
    identifier_pattern: str = Field(
        ...,
        description="Ltree pattern to match (e.g., 'itpcp.progphys.py.*'). Uses * for single-level wildcard.",
        examples=["itpcp.progphys.py.*", "itp.*", "section.topic.*"]
    )
    repository_id: Optional[str] = Field(
        None,
        description="Optional: scope deletion to specific repository"
    )
    dry_run: bool = Field(
        False,
        description="If true, only returns preview without deleting"
    )
    force_level: ForceLevel = Field(
        ForceLevel.NONE,
        description="Force level: 'none' blocks if active deployments, 'old' allows archived/failed, 'all' deletes active (requires confirmation)"
    )


class ExampleBulkDeleteResult(BaseModel):
    """Result of bulk example deletion operation."""
    dry_run: bool = Field(..., description="Whether this was a preview only")
    pattern_matched: str = Field(..., description="Pattern that was used for matching")
    repository_id: Optional[str] = Field(
        None, description="Repository scope if specified"
    )
    examples_affected: int = Field(0, description="Number of examples deleted")
    versions_deleted: int = Field(0, description="Total versions deleted")
    dependencies_deleted: int = Field(0, description="Example dependencies deleted")
    storage_objects_deleted: int = Field(0, description="MinIO objects deleted")
    deployment_references_orphaned: int = Field(
        0, description="Deployments with example_version_id set to NULL"
    )
    examples: List[ExampleDeletePreview] = Field(
        default_factory=list,
        description="Details of examples affected"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Errors encountered during deletion"
    )
