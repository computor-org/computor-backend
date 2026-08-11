"""Minimal DTOs for tutor testing - ephemeral test runs for debugging."""

from typing import List, Optional, Literal, Any
from pydantic import BaseModel, ConfigDict, Field
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
    """Quick status check for a tutor test run (for polling)."""
    test_id: str
    status: Literal["pending", "running", "completed", "failed", "timeout"]
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    has_artifacts: bool = False
    artifact_count: int = 0


class TutorTestGet(BaseModel):
    """Full tutor test details including result_dict from MinIO."""
    test_id: str
    status: Literal["pending", "running", "completed", "failed", "timeout"]
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    # Full test result from result.json in MinIO
    result_dict: Optional[Any] = None
    # Convenience fields extracted from result_dict
    passed: Optional[int] = None
    failed: Optional[int] = None
    total: Optional[int] = None
    result_value: Optional[float] = None
    error: Optional[str] = None
    # Artifact info
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


class TutorTestResultSummary(BaseModel):
    """Test counts as reported by the testing framework."""
    total: Optional[int] = None
    passed: Optional[int] = None
    failed: Optional[int] = None
    skipped: Optional[int] = None


class TutorTestResultSubmit(BaseModel):
    """Body of ``POST /tutors/tests/{test_id}/results``.

    Posted by the testing worker once a run finishes. The document is stored
    verbatim as ``result.json`` in MinIO and handed back out again as
    ``TutorTestGet.result_dict``, so unknown keys are *preserved* rather than
    rejected — only the fields the backend itself reads are declared here.
    Counts arrive either nested under ``summary`` or flat at the top level,
    depending on the language runner; both are accepted.
    """
    model_config = ConfigDict(extra="allow")

    summary: Optional[TutorTestResultSummary] = None
    total: Optional[int] = None
    passed: Optional[int] = None
    failed: Optional[int] = None
    result_value: Optional[float] = None
    error: Optional[str] = None