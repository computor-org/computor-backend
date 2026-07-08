"""Business logic for student profile operations.

Thin wrapper over the shared owner-scoped CRUD skeleton (TASK-206). The
permission decisions are BIT-IDENTICAL to the pre-refactor implementation.

DIVERGENCES from ``business_logic/profiles.py`` (preserved verbatim, NOT
unified away):

* the manage capability is ``student_profile:list`` (a different resource);
* ``create``/``update``/``delete`` require that manage capability up front and
  raise ``403`` for everyone else — regular owners cannot create/update/delete
  their own student profile, unlike plain profiles;
* ``create`` carries EXTRA owner-resolution: ``user_id`` defaults to the
  caller when omitted, an ``organization_id`` is required, and uniqueness is
  scoped to ``(user_id, organization_id)``;
* results are returned as DTOs.
"""
from uuid import UUID
from typing import Tuple, List

from sqlalchemy.orm import Session

from computor_backend.exceptions import ForbiddenException, BadRequestException
from computor_backend.permissions.principal import Principal
from computor_backend.model.auth import StudentProfile
from computor_types.student_profile import (
    StudentProfileGet, StudentProfileList, StudentProfileUpdate,
    StudentProfileCreate, StudentProfileQuery
)
from computor_backend.interfaces import StudentProfileInterface
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

# General-claim resource gating "manage all student profiles". Distinct from
# the plain-profile resource on purpose (see ownership.py).
_RESOURCE = "student_profile"


def has_profile_permission(permissions: Principal) -> bool:
    """Check if user has general permission to manage all student profiles."""
    return has_manage_permission(permissions, _RESOURCE)


def can_access_profile(permissions: Principal, profile: StudentProfile) -> bool:
    """Check if user can access a specific student profile."""
    return is_owner_or_manager(permissions, profile.user_id, _RESOURCE)


def list_profiles(
    permissions: Principal,
    params: StudentProfileQuery,
    db: Session,
) -> Tuple[List[StudentProfileList], int]:
    """List student profiles with permission filtering."""
    profiles, total = list_owned(
        db=db,
        model=StudentProfile,
        interface=StudentProfileInterface,
        permissions=permissions,
        params=params,
        resource=_RESOURCE,
    )
    return [StudentProfileList.model_validate(p, from_attributes=True) for p in profiles], total


def get_profile(
    profile_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> StudentProfileGet:
    """Get a student profile by ID with permission check."""
    profile = get_owned_or_404(
        db=db,
        model=StudentProfile,
        entity_id=profile_id,
        permissions=permissions,
        resource=_RESOURCE,
        not_found_detail="Student profile not found",
    )
    return StudentProfileGet.model_validate(profile, from_attributes=True)


def create_profile(
    data: StudentProfileCreate,
    permissions: Principal,
    db: Session,
) -> StudentProfileGet:
    """Create a student profile with permission enforcement."""
    # Only admins and users with general permissions can create student profiles.
    # Regular students/users CANNOT create profiles. (DIVERGENCE from profiles.)
    if not has_profile_permission(permissions):
        raise ForbiddenException(detail="Only admins and user managers can create student profiles")

    # EXTRA owner-resolution (preserved verbatim): default to the current user
    # when no user_id is provided.
    target_user_id = data.user_id if data.user_id else str(permissions.user_id)

    # Check if profile already exists for this user in this organization.
    # Note: Users can have multiple student profiles (one per organization).
    if not data.organization_id:
        raise BadRequestException(detail="organization_id is required to create a student profile")

    existing = db.query(StudentProfile).filter(
        StudentProfile.user_id == target_user_id,
        StudentProfile.organization_id == data.organization_id
    ).first()
    if existing:
        raise BadRequestException(
            detail=f"Student profile already exists for this user in organization {data.organization_id}"
        )

    def _build() -> StudentProfile:
        profile_data = data.model_dump(exclude_unset=True)
        profile_data['user_id'] = target_user_id
        return StudentProfile(**profile_data)

    profile = persist_new(
        db=db,
        factory=_build,
        error_detail="Failed to create student profile",
        log_context="Error creating student profile",
    )
    return StudentProfileGet.model_validate(profile, from_attributes=True)


def update_profile(
    profile_id: UUID | str,
    data: StudentProfileUpdate,
    permissions: Principal,
    db: Session,
) -> StudentProfileGet:
    """Update a student profile with permission check."""
    # Only admins and users with general permissions can update student profiles.
    # Regular students/users CANNOT update profiles. (DIVERGENCE from profiles:
    # 403 manager-gate BEFORE the row is fetched.)
    if not has_profile_permission(permissions):
        raise ForbiddenException(detail="Only admins and user managers can update student profiles")

    profile = get_owned_or_404(
        db=db,
        model=StudentProfile,
        entity_id=profile_id,
        permissions=permissions,
        resource=_RESOURCE,
        not_found_detail="Student profile not found",
    )

    update_data = data.model_dump(exclude_unset=True)
    profile = apply_update(
        db=db,
        obj=profile,
        update_data=update_data,
        error_detail="Failed to update student profile",
        log_context="Error updating student profile",
    )
    return StudentProfileGet.model_validate(profile, from_attributes=True)


def delete_profile(
    profile_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> None:
    """Delete a student profile with permission check."""
    # Only admins and users with general permissions can delete student profiles.
    # Regular students/users CANNOT delete profiles. (DIVERGENCE from profiles:
    # 403 manager-gate BEFORE the row is fetched.)
    if not has_profile_permission(permissions):
        raise ForbiddenException(detail="Only admins and user managers can delete student profiles")

    profile = get_owned_or_404(
        db=db,
        model=StudentProfile,
        entity_id=profile_id,
        permissions=permissions,
        resource=_RESOURCE,
        not_found_detail="Student profile not found",
    )
    delete_owned(
        db=db,
        obj=profile,
        error_detail="Failed to delete student profile",
        log_context="Error deleting student profile",
    )
