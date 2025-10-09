"""Business logic for user profiles management."""
import logging
from uuid import UUID
from typing import List, Tuple

from sqlalchemy.orm import Session

from computor_backend.api.exceptions import NotFoundException, ForbiddenException, BadRequestException
from computor_backend.model.auth import Profile
from computor_backend.permissions.principal import Principal
from computor_types.profiles import ProfileQuery
from computor_backend.interfaces import ProfileInterface

logger = logging.getLogger(__name__)


def has_profile_permission(permissions: Principal) -> bool:
    """Check if user has general permission to manage all profiles."""
    return permissions.is_admin or permissions.has_general_permission("profile", "list")


def can_access_profile(permissions: Principal, profile: Profile) -> bool:
    """Check if user can access a specific profile."""
    if has_profile_permission(permissions):
        return True
    return str(profile.user_id) == str(permissions.user_id)


def list_profiles(
    permissions: Principal,
    params: ProfileQuery,
    db: Session,
) -> Tuple[List[Profile], int]:
    """List profiles - admins/_user_manager see all, users see only their own."""

    query = db.query(Profile)

    # Apply permission filtering
    if not has_profile_permission(permissions):
        query = query.filter(Profile.user_id == permissions.user_id)

    # Apply search filters using the interface search function
    query = ProfileInterface.search(db, query, params)

    # Get total count
    total = query.count()

    # Apply pagination
    if params.limit:
        query = query.limit(params.limit)
    if params.skip:
        query = query.offset(params.skip)

    profiles = query.all()
    return profiles, total


def get_profile(
    profile_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> Profile:
    """Get a profile by ID - users can only get their own, admins/_user_manager can get any."""

    profile = db.query(Profile).filter(Profile.id == profile_id).first()

    if not profile:
        raise NotFoundException(detail="Profile not found")

    if not can_access_profile(permissions, profile):
        raise NotFoundException(detail="Profile not found")

    return profile


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

    try:
        profile = Profile(**profile_data)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return profile
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating profile: {e}")
        raise BadRequestException(detail=str(e))


def update_profile(
    profile_id: UUID | str,
    update_data: dict,
    permissions: Principal,
    db: Session,
) -> Profile:
    """Update a profile - users can only update their own, admins/_user_manager can update any."""

    profile = db.query(Profile).filter(Profile.id == profile_id).first()

    if not profile:
        raise NotFoundException(detail="Profile not found")

    if not can_access_profile(permissions, profile):
        raise NotFoundException(detail="Profile not found")

    try:
        for key, value in update_data.items():
            setattr(profile, key, value)

        db.commit()
        db.refresh(profile)
        return profile
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating profile: {e}")
        raise BadRequestException(detail=str(e))


def delete_profile(
    profile_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> None:
    """Delete a profile - users can only delete their own, admins/_user_manager can delete any."""

    profile = db.query(Profile).filter(Profile.id == profile_id).first()

    if not profile:
        raise NotFoundException(detail="Profile not found")

    if not can_access_profile(permissions, profile):
        raise NotFoundException(detail="Profile not found")

    try:
        db.delete(profile)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting profile: {e}")
        raise BadRequestException(detail=str(e))
