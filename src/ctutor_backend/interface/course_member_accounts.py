"""DTOs for managing external provider accounts attached to course members."""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional


class CourseMemberProviderAccountUpdate(BaseModel):
    """Request payload to set or update a provider account for a course member."""

    provider_account_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Account identifier on the external provider (e.g., GitLab username)",
    )
    provider_access_token: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=4096,
        description="Personal access token or credential to verify provider ownership",
    )

    model_config = ConfigDict(str_strip_whitespace=True)


class CourseMemberReadinessStatus(BaseModel):
    """Readiness state for a course member to start working on provider-backed tasks."""

    course_member_id: str
    course_id: str
    organization_id: str
    course_role_id: str
    provider_type: Optional[str] = None
    provider: Optional[str] = None
    requires_account: bool
    has_account: bool
    is_ready: bool
    provider_account_id: Optional[str] = None
    provider_access_token: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CourseMemberValidationRequest(BaseModel):
    """Validation parameters supplied when checking provider readiness."""

    provider_access_token: Optional[str] = Field(
        default=None,
        description="Access token or credential used to validate provider ownership",
    )

    model_config = ConfigDict(str_strip_whitespace=True)
