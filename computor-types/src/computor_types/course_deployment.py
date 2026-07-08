"""DTOs for deploying a single course from an uploaded ``course_deployment.yaml``.

The web "create course" page can optionally upload a course-level deployment
file — a top-level :class:`~computor_types.deployment_config.HierarchicalCourseConfig`
(``name``, ``path``, ``services``, ``content_types`` and a nested ``contents``
tree), with no organization/git/users keys. The file is first *validated*
(``validate_only=True``) and then *applied* under an existing course family.

These are plain request/response models (not registered CRUD entities).
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class CourseDeployRequest(BaseModel):
    """Upload payload for the course-deployment endpoint.

    The raw YAML text is sent as-is and parsed server-side into a
    ``HierarchicalCourseConfig`` — the client never needs to model the schema.
    """

    yaml: str = Field(..., description="Raw contents of the course_deployment.yaml file")
    validate_only: bool = Field(
        False,
        description="When true, parse and check the config (examples resolve, content types exist, "
        "path free) without creating anything.",
    )


class CourseDeployWarning(BaseModel):
    """A non-fatal issue found while validating/applying the config.

    Warnings never block a deploy; the affected content is still created (just
    without an example, typically)."""

    path: Optional[str] = Field(None, description="Dotted course-content path the warning relates to")
    example_identifier: Optional[str] = Field(None, description="Example identifier the warning relates to")
    reason: str = Field(..., description="Human-readable explanation")


class CourseDeploySummary(BaseModel):
    """Counts of what was (or would be) created."""

    content_types: int = Field(0, description="Number of content types")
    units: int = Field(0, description="Number of non-submittable contents (units)")
    assignments: int = Field(0, description="Number of submittable contents (assignments)")
    examples_assigned: int = Field(0, description="Number of examples assigned to assignments")


class CourseDeployResult(BaseModel):
    """Outcome of a validate or apply run."""

    validated: bool = Field(..., description="Whether the config parsed and the checks ran")
    applied: bool = Field(..., description="Whether the course was actually created")
    course_id: Optional[str] = Field(None, description="ID of the created course (apply only)")
    course_path: str = Field(..., description="Course path/slug from the file")
    course_title: Optional[str] = Field(None, description="Course title/name from the file")
    summary: CourseDeploySummary = Field(default_factory=CourseDeploySummary)
    warnings: List[CourseDeployWarning] = Field(default_factory=list)
    errors: List[str] = Field(
        default_factory=list,
        description="Fatal problems that block an apply (e.g. unknown content type, path taken)",
    )
