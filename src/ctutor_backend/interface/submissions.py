"""Pydantic DTOs for manual submission endpoints."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class SubmissionCreate(BaseModel):
    """Payload describing a manual submission request."""

    course_submission_group_id: str
    version_identifier: Optional[str] = None


class SubmissionUploadedFile(BaseModel):
    """Metadata about a file extracted from a submission archive."""

    object_key: str
    size: int
    content_type: str
    relative_path: str


class SubmissionUploadResponseModel(BaseModel):
    """Response returned after processing a manual submission."""

    result_id: UUID
    bucket_name: str
    files: List[SubmissionUploadedFile]
    total_size: int
    submitted_at: datetime
    version_identifier: str
