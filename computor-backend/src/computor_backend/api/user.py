from typing import Annotated, Optional, List
from uuid import UUID

import logging
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_types.cascade_deletion import CascadeDeleteResult
from computor_types.course_member_accounts import (
    CourseMemberProviderAccountUpdate,
    CourseMemberReadinessStatus,
    CourseMemberValidationRequest,
)
from computor_types.users import UserGet, UserPassword
from computor_backend.exceptions.exceptions import ForbiddenException, NotFoundException
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal
from computor_backend.business_logic.cascade_deletion import delete_user_cascade
from computor_backend.services.storage_service import get_storage_service
from computor_backend.model.auth import User as UserModel
from fastapi import APIRouter, Depends, Query

# Import business logic
from computor_backend.business_logic.users import (
    get_current_user,
    set_user_password,
    get_course_views_for_user,
    get_course_views_for_user_by_course,
    validate_user_course,
    register_user_course_account,
)

logger = logging.getLogger(__name__)

user_router = APIRouter()

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

@user_router.get(
    "/views/{course_id}",
    response_model=List[str],
)
async def get_course_views_for_current_user_by_course(
    course_id: UUID | str,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
):
    """Get available views based on role for a specific course for the current user."""
    user_id = permissions.get_user_id()
    if not user_id:
        return []

    return get_course_views_for_user_by_course(user_id, course_id, db)

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


@user_router.delete(
    "/{user_id}",
    response_model=CascadeDeleteResult,
)
async def delete_user_endpoint(
    user_id: UUID,
    permissions: Annotated[Principal, Depends(get_current_principal)],
    db: Session = Depends(get_db),
    dry_run: bool = Query(
        default=False,
        description="If true, only returns preview of what would be deleted"
    ),
) -> CascadeDeleteResult:
    """Delete a user and all their related data. Admin only."""
    if not permissions.is_admin:
        raise ForbiddenException("User deletion requires admin permissions")

    # Prevent self-deletion
    if str(user_id) == str(permissions.user_id):
        raise ForbiddenException("Cannot delete your own account")

    # Verify user exists
    user = db.query(UserModel).filter(UserModel.id == str(user_id)).first()
    if not user:
        raise NotFoundException(f"User not found: {user_id}")

    storage = get_storage_service()
    return await delete_user_cascade(
        db=db,
        user_id=str(user_id),
        storage=storage,
        dry_run=dry_run,
    )
