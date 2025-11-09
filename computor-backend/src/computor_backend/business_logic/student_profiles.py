"""Business logic for student profile operations."""
from uuid import UUID
from typing import Tuple, List
from sqlalchemy.orm import Session, Query

from computor_backend.api.exceptions import NotFoundException, ForbiddenException, BadRequestException
from computor_backend.permissions.principal import Principal
from computor_backend.model.auth import StudentProfile
from computor_types.student_profile import (
    StudentProfileGet, StudentProfileList, StudentProfileUpdate,
    StudentProfileCreate, StudentProfileQuery
)
from computor_backend.interfaces import StudentProfileInterface


def has_profile_permission(permissions: Principal) -> bool:
    """Check if user has general permission to manage all student profiles.

    Args:
        permissions: Current user permissions

    Returns:
        True if user can manage all student profiles
    """
    return permissions.is_admin or permissions.has_general_permission("student_profile", "list")


def can_access_profile(permissions: Principal, profile: StudentProfile) -> bool:
    """Check if user can access a specific student profile.

    Args:
        permissions: Current user permissions
        profile: Student profile to check access for

    Returns:
        True if user can access this specific profile
    """
    if has_profile_permission(permissions):
        return True
    return str(profile.user_id) == str(permissions.user_id)


def list_profiles(
    permissions: Principal,
    params: StudentProfileQuery,
    db: Session,
) -> Tuple[List[StudentProfileList], int]:
    """List student profiles with permission filtering.

    Args:
        permissions: Current user permissions
        params: Query parameters
        db: Database session

    Returns:
        Tuple of (profile list, total count)
    """
    query = db.query(StudentProfile)

    # Apply permission filtering
    if not has_profile_permission(permissions):
        query = query.filter(StudentProfile.user_id == permissions.user_id)

    # Apply search filters using the interface search function
    query = StudentProfileInterface.search(db, query, params)

    # Get total count
    total = query.count()

    # Apply pagination
    if params.limit:
        query = query.limit(params.limit)
    if params.skip:
        query = query.offset(params.skip)

    profiles = query.all()
    return [StudentProfileList.model_validate(p, from_attributes=True) for p in profiles], total


def get_profile(
    profile_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> StudentProfileGet:
    """Get a student profile by ID with permission check.

    Args:
        profile_id: Profile ID
        permissions: Current user permissions
        db: Database session

    Returns:
        Student profile

    Raises:
        NotFoundException: If profile not found or user lacks access
    """
    profile = db.query(StudentProfile).filter(StudentProfile.id == profile_id).first()

    if not profile:
        raise NotFoundException(detail="Student profile not found")

    if not can_access_profile(permissions, profile):
        raise NotFoundException(detail="Student profile not found")

    return StudentProfileGet.model_validate(profile, from_attributes=True)


def create_profile(
    data: StudentProfileCreate,
    permissions: Principal,
    db: Session,
) -> StudentProfileGet:
    """Create a student profile with permission enforcement.

    Args:
        data: Profile creation data
        permissions: Current user permissions
        db: Database session

    Returns:
        Created student profile

    Raises:
        ForbiddenException: If user lacks permission
        BadRequestException: If profile already exists or creation fails
    """
    # Only admins and users with general permissions can create student profiles
    # Regular students/users CANNOT create profiles
    if not has_profile_permission(permissions):
        raise ForbiddenException(detail="Only admins and user managers can create student profiles")

    # If no user_id provided, default to current user
    target_user_id = data.user_id if data.user_id else str(permissions.user_id)

    # Check if profile already exists for this user in this organization
    # Note: Users can have multiple student profiles (one per organization)
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

    try:
        profile_data = data.model_dump(exclude_unset=True)
        profile_data['user_id'] = target_user_id
        profile = StudentProfile(**profile_data)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return StudentProfileGet.model_validate(profile, from_attributes=True)
    except Exception as e:
        db.rollback()
        raise BadRequestException(detail=str(e))


def update_profile(
    profile_id: UUID | str,
    data: StudentProfileUpdate,
    permissions: Principal,
    db: Session,
) -> StudentProfileGet:
    """Update a student profile with permission check.

    Args:
        profile_id: Profile ID
        data: Update data
        permissions: Current user permissions
        db: Database session

    Returns:
        Updated student profile

    Raises:
        NotFoundException: If profile not found or user lacks access
        ForbiddenException: If user lacks permission to update
        BadRequestException: If update fails
    """
    # Only admins and users with general permissions can update student profiles
    # Regular students/users CANNOT update profiles
    if not has_profile_permission(permissions):
        raise ForbiddenException(detail="Only admins and user managers can update student profiles")

    profile = db.query(StudentProfile).filter(StudentProfile.id == profile_id).first()

    if not profile:
        raise NotFoundException(detail="Student profile not found")

    if not can_access_profile(permissions, profile):
        raise NotFoundException(detail="Student profile not found")

    try:
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(profile, key, value)

        db.commit()
        db.refresh(profile)
        return StudentProfileGet.model_validate(profile, from_attributes=True)
    except Exception as e:
        db.rollback()
        raise BadRequestException(detail=str(e))


def delete_profile(
    profile_id: UUID | str,
    permissions: Principal,
    db: Session,
) -> None:
    """Delete a student profile with permission check.

    Args:
        profile_id: Profile ID
        permissions: Current user permissions
        db: Database session

    Raises:
        NotFoundException: If profile not found or user lacks access
        ForbiddenException: If user lacks permission to delete
        BadRequestException: If deletion fails
    """
    # Only admins and users with general permissions can delete student profiles
    # Regular students/users CANNOT delete profiles
    if not has_profile_permission(permissions):
        raise ForbiddenException(detail="Only admins and user managers can delete student profiles")

    profile = db.query(StudentProfile).filter(StudentProfile.id == profile_id).first()

    if not profile:
        raise NotFoundException(detail="Student profile not found")

    if not can_access_profile(permissions, profile):
        raise NotFoundException(detail="Student profile not found")

    try:
        db.delete(profile)
        db.commit()
    except Exception as e:
        db.rollback()
        raise BadRequestException(detail=str(e))
