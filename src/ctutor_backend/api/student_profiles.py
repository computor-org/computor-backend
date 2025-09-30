from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ctutor_backend.api.exceptions import NotFoundException, ForbiddenException, BadRequestException
from ctutor_backend.database import get_db
from ctutor_backend.interface.student_profile import (
    StudentProfileGet, StudentProfileList, StudentProfileUpdate,
    StudentProfileCreate, StudentProfileQuery, student_profile_search
)
from ctutor_backend.model.auth import StudentProfile
from ctutor_backend.permissions.auth import get_current_principal
from ctutor_backend.permissions.principal import Principal

student_profile_router = APIRouter()


def _has_student_profile_permission(permissions: Principal) -> bool:
    """Check if user has general permission to manage all student profiles"""
    return permissions.is_admin or permissions.has_general_permission("student_profile", "list")


def _can_access_student_profile(permissions: Principal, profile: StudentProfile) -> bool:
    """Check if user can access a specific student profile"""
    if _has_student_profile_permission(permissions):
        return True
    return str(profile.user_id) == str(permissions.user_id)


@student_profile_router.get("", response_model=list[StudentProfileList])
async def list_student_profiles(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    response: Response,
    params: StudentProfileQuery = Depends(),
    db: Session = Depends(get_db)
):
    """List student profiles - admins/_user_manager see all, users see only their own"""
    query = db.query(StudentProfile)

    # Apply permission filtering
    if not _has_student_profile_permission(permissions):
        query = query.filter(StudentProfile.user_id == permissions.user_id)

    # Apply search filters using the interface search function
    query = student_profile_search(db, query, params)

    # Get total count
    total = query.count()
    response.headers["X-Total-Count"] = str(total)

    # Apply pagination
    if params.limit:
        query = query.limit(params.limit)
    if params.skip:
        query = query.offset(params.skip)

    profiles = query.all()
    return [StudentProfileList.model_validate(p, from_attributes=True) for p in profiles]


@student_profile_router.get("/{id}", response_model=StudentProfileGet)
async def get_student_profile(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    id: UUID | str,
    db: Session = Depends(get_db)
):
    """Get a student profile by ID - users can only get their own, admins/_user_manager can get any"""
    profile = db.query(StudentProfile).filter(StudentProfile.id == id).first()

    if not profile:
        raise NotFoundException(detail="Student profile not found")

    if not _can_access_student_profile(permissions, profile):
        raise NotFoundException(detail="Student profile not found")

    return StudentProfileGet.model_validate(profile, from_attributes=True)


@student_profile_router.post("", response_model=StudentProfileGet, status_code=201)
async def create_student_profile(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    data: StudentProfileCreate,
    db: Session = Depends(get_db)
):
    print("asdf")
    """Create a student profile - users can create for themselves (user_id optional), admins/_user_manager can create for anyone"""
    # If no user_id provided, default to current user
    target_user_id = data.user_id if data.user_id else str(permissions.user_id)

    # Check if user is trying to create for someone else
    if str(target_user_id) != str(permissions.user_id):
        if not _has_student_profile_permission(permissions):
            raise ForbiddenException(detail="Cannot create student profile for another user")

    # Check if profile already exists for this user
    existing = db.query(StudentProfile).filter(StudentProfile.user_id == target_user_id).first()
    if existing:
        raise BadRequestException(detail="Student profile already exists for this user")

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


@student_profile_router.patch("/{id}", response_model=StudentProfileGet)
async def update_student_profile(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    id: UUID | str,
    data: StudentProfileUpdate,
    db: Session = Depends(get_db)
):
    """Update a student profile - users can only update their own, admins/_user_manager can update any"""
    profile = db.query(StudentProfile).filter(StudentProfile.id == id).first()

    if not profile:
        raise NotFoundException(detail="Student profile not found")

    if not _can_access_student_profile(permissions, profile):
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


@student_profile_router.delete("/{id}", status_code=204)
async def delete_student_profile(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    id: UUID | str,
    db: Session = Depends(get_db)
):
    """Delete a student profile - users can only delete their own, admins/_user_manager can delete any"""
    profile = db.query(StudentProfile).filter(StudentProfile.id == id).first()

    if not profile:
        raise NotFoundException(detail="Student profile not found")

    if not _can_access_student_profile(permissions, profile):
        raise NotFoundException(detail="Student profile not found")

    try:
        db.delete(profile)
        db.commit()
    except Exception as e:
        db.rollback()
        raise BadRequestException(detail=str(e))