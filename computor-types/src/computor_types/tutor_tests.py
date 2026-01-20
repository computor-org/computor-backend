"""Minimal DTOs for tutor testing - ephemeral test runs for debugging."""

from typing import List, Optional, Literal, Any
from pydantic import BaseModel, Field
from datetime import datetime


class TutorTestConfig(BaseModel):
    """Optional configuration for tutor test (passed as JSON in form data)."""
    store_graphics_artifacts: bool = Field(default=True)
    timeout_seconds: Optional[int] = Field(default=None)


class TutorTestCreateResponse(BaseModel):
    """Response when creating a tutor test - just the essentials."""
    test_id: str
    status: Literal["pending", "running", "completed", "failed", "timeout"] = "pending"
    created_at: Optional[datetime] = None


class TutorTestStatus(BaseModel):
    """Status of a tutor test run."""
    test_id: str
    status: Literal["pending", "running", "completed", "failed", "timeout"]
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    result: Optional[Any] = None  # Test result details
    error: Optional[str] = None  # Error message if failed
    has_artifacts: bool = False
    artifact_count: int = 0


class TutorTestArtifactInfo(BaseModel):
    """Information about a single artifact."""
    filename: str
    size: int
    last_modified: Optional[datetime] = None


class TutorTestArtifactList(BaseModel):
    """List of artifacts from a tutor test."""
    test_id: str
    artifacts: List[TutorTestArtifactInfo] = []
    total_count: int = 0