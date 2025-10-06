from typing import Annotated, Optional, List
from uuid import UUID

import logging
from pydantic import BaseModel
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_types.course_member_accounts import (
    CourseMemberProviderAccountUpdate,
    CourseMemberReadinessStatus,
    CourseMemberValidationRequest,
)
from computor_types.users import UserGet
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from fastapi import APIRouter, Depends

# Import business logic
from computor_backend.business_logic.users import (
    get_current_user,
    set_user_password,
    get_course_views_for_user,
    validate_user_course,
    register_user_course_account,
)

logger = logging.getLogger(__name__)

user_router = APIRouter()

class UserPassword(BaseModel):
    username: Optional[str] = None
    password: str
    password_old: Optional[str] = None


@user_router.get("", response_model=UserGet)
def get_current_user_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db)
):
    """Get the current authenticated user."""
    return get_current_user(permissions.user_id, db)


@user_router.post("/password", status_code=204)
def set_user_password_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    payload: UserPassword,
    db: Session = Depends(get_db)
):
    """Set or update user password."""
    set_user_password(
        target_username=payload.username,
        new_password=payload.password,
        old_password=payload.password_old,
        permissions=permissions,
        db=db,
    )


@user_router.get(
    "/views",
    response_model=List[str],
)
async def get_course_views_for_current_user(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Get available views based on roles across all courses for the current user."""
    user_id = permissions.get_user_id()
    if not user_id:
        return []

    return get_course_views_for_user(user_id, db)


@user_router.post(
    "/courses/{course_id}/validate",
    response_model=CourseMemberReadinessStatus,
)
async def validate_current_user_course(
    course_id: UUID | str,
    validation: CourseMemberValidationRequest,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Validate user's course membership and provider account."""
    return validate_user_course(
        course_id=course_id,
        provider_access_token=validation.provider_access_token if validation else None,
        permissions=permissions,
        db=db,
    )


@user_router.post(
    "/courses/{course_id}/register",
    response_model=CourseMemberReadinessStatus,
)
async def register_current_user_course_account(
    course_id: UUID | str,
    payload: CourseMemberProviderAccountUpdate,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Register user's provider account for a course."""
    return register_user_course_account(
        course_id=course_id,
        provider_account_id=payload.provider_account_id,
        provider_access_token=payload.provider_access_token,
        permissions=permissions,
        db=db,
    )
