from typing import Optional
from pydantic import BaseModel
from computor_types.repositories import Repository

class TestJob(BaseModel):
    user_id: str
    course_member_id: str
    course_content_id: str
    testing_service_id: str  # UUID of the Service (e.g., itp-worker-python)
    testing_service_slug: str  # Service slug
    testing_service_type_path: str  # ServiceType path (e.g., testing.python)
    module: Repository
    reference: Optional[Repository] = None

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