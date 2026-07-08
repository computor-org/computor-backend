"""Business logic for user profiles management.

Thin wrapper over the shared owner-scoped CRUD skeleton (TASK-206). The
permission decisions are BIT-IDENTICAL to the pre-refactor implementation:
the manage capability is ``profile:list`` (or admin), owners may read/write
their own profile, and non-owners without that capability get a 404 on
get/update/delete.
"""
from uuid import UUID
from typing import List, Tuple

from sqlalchemy.orm import Session

from computor_backend.exceptions import ForbiddenException, BadRequestException
from computor_backend.model.auth import Profile
from computor_backend.permissions.principal import Principal
from computor_types.profiles import ProfileQuery
from computor_backend.interfaces import ProfileInterface
from computor_backend.business_logic.ownership import (
    has_manage_permission,
    is_owner_or_manager,
)
from computor_backend.business_logic._owned_crud import (
    list_owned,
    get_owned_or_404,
    persist_new,
    apply_update,
    delete_owned,
)

# General-claim resource gating "manage all profiles". Kept distinct from the
# student-profile resource on purpose (see ownership.py).
_RESOURCE = "profile"


def has_profile_permission(permissions: Principal) -> bool:
    """Check if user has general permission to manage all profiles."""
    return has_manage_permission(permissions, _RESOURCE)


def can_access_profile(permissions: Principal, profile: Profile) -> bool:
    """Check if user can access a specific profile."""
    return is_owner_or_manager(permissions, profile.user_id, _RESOURCE)


def list_profiles(
    permissions: Principal,
    params: ProfileQuery,
    db: Session,
) -> Tuple[List[Profile], int]:
    """List profiles - admins/_user_manager see all, users see only their own."""
    return list_owned(
        db=db,
        model=Profile,
        interface=ProfileInterface,
        permissions=permissions,
        params=params,
        resource=_RESOURCE,
    )


def get_profile(
    profile_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> Profile:
    """Get a profile by ID - users can only get their own, admins/_user_manager can get any."""
    return get_owned_or_404(
        db=db,
        model=Profile,
        entity_id=profile_id,
        permissions=permissions,
        resource=_RESOURCE,
        not_found_detail="Profile not found",
    )


def create_profile(
    user_id: UUID | str,
    profile_data: dict,
    permissions: Principal,
    db: Session,
) -> Profile:
    """Create a profile - users can create for themselves, admins/_user_manager can create for anyone."""

    # Check if user is trying to create for someone else
    if str(user_id) != str(permissions.user_id):
        if not has_profile_permission(permissions):
            raise ForbiddenException(detail="Cannot create profile for another user")

    # Check if profile already exists for this user
    existing = db.query(Profile).filter(Profile.user_id == user_id).first()
    if existing:
        raise BadRequestException(detail="Profile already exists for this user")

    return persist_new(
        db=db,
        factory=lambda: Profile(**profile_data),
        error_detail="Failed to create profile",
        log_context="Error creating profile",
    )


def update_profile(
    profile_id: UUID | str,
    update_data: dict,
    permissions: Principal,
    db: Session,
) -> Profile:
    """Update a profile - users can only update their own, admins/_user_manager can update any."""
    profile = get_owned_or_404(
        db=db,
        model=Profile,
        entity_id=profile_id,
        permissions=permissions,
        resource=_RESOURCE,
        not_found_detail="Profile not found",
    )
    return apply_update(
        db=db,
        obj=profile,
        update_data=update_data,
        error_detail="Failed to update profile",
        log_context="Error updating profile",
    )


def delete_profile(
    profile_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> None:
    """Delete a profile - users can only delete their own, admins/_user_manager can delete any."""
    profile = get_owned_or_404(
        db=db,
        model=Profile,
        entity_id=profile_id,
        permissions=permissions,
        resource=_RESOURCE,
        not_found_detail="Profile not found",
    )
    delete_owned(
        db=db,
        obj=profile,
        error_detail="Failed to delete profile",
        log_context="Error deleting profile",
    )
