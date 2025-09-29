from typing import Optional
from pydantic import BaseModel
from ctutor_backend.interface.repositories import Repository

class TestJob(BaseModel):
    user_id: str
    course_member_id: str
    course_content_id: str
    execution_backend_id: str
    execution_backend_type: str
    module: Repository
    reference: Optional[Repository] = None
    test_number: int = -1
    submission_number: int = -1

class TestCreate(BaseModel):
    # Primary way to specify what to test - provide the artifact ID directly
    artifact_id: Optional[str] = None

    # Alternative: specify submission group and optionally version to find artifact
    submission_group_id: Optional[str] = None
    version_identifier: Optional[str] = None  # If not provided with submission_group_id, uses latest

    # Legacy fields for backward compatibility
    course_member_id: Optional[str] = None
    course_content_id: Optional[str] = None
    course_content_path: Optional[str] = None

    directory: Optional[str] = None
    project: Optional[str] = None
    provider_url: Optional[str] = None

    submit: Optional[bool] = None