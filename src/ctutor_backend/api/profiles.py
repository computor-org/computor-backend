from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ctutor_backend.api.exceptions import NotFoundException, ForbiddenException, BadRequestException
from ctutor_backend.database import get_db
from ctutor_backend.interface.profiles import (
    ProfileGet, ProfileList, ProfileUpdate, ProfileCreate,
    ProfileQuery, profile_search
)
from ctutor_backend.model.auth import Profile
from ctutor_backend.permissions.auth import get_current_principal
from ctutor_backend.permissions.principal import Principal

profile_router = APIRouter()


def _has_profile_permission(permissions: Principal) -> bool:
    """Check if user has general permission to manage all profiles"""
    return permissions.is_admin or permissions.has_general_permission("profile", "list")


def _can_access_profile(permissions: Principal, profile: Profile) -> bool:
    """Check if user can access a specific profile"""
    if _has_profile_permission(permissions):
        return True
    return str(profile.user_id) == str(permissions.user_id)


@profile_router.get("", response_model=list[ProfileList])
async def list_profiles(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    response: Response,
    params: ProfileQuery = Depends(),
    db: Session = Depends(get_db)
):
    """List profiles - admins/_user_manager see all, users see only their own"""
    query = db.query(Profile)

    # Apply permission filtering
    if not _has_profile_permission(permissions):
        query = query.filter(Profile.user_id == permissions.user_id)

    # Apply search filters using the interface search function
    query = profile_search(db, query, params)

    # Get total count
    total = query.count()
    response.headers["X-Total-Count"] = str(total)

    # Apply pagination
    if params.limit:
        query = query.limit(params.limit)
    if params.skip:
        query = query.offset(params.skip)

    profiles = query.all()
    return [ProfileList.model_validate(p, from_attributes=True) for p in profiles]


@profile_router.get("/{id}", response_model=ProfileGet)
async def get_profile(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    id: UUID | str,
    db: Session = Depends(get_db)
):
    """Get a profile by ID - users can only get their own, admins/_user_manager can get any"""
    profile = db.query(Profile).filter(Profile.id == id).first()

    if not profile:
        raise NotFoundException(detail="Profile not found")

    if not _can_access_profile(permissions, profile):
        raise NotFoundException(detail="Profile not found")

    return ProfileGet.model_validate(profile, from_attributes=True)


@profile_router.post("", response_model=ProfileGet, status_code=201)
async def create_profile(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    data: ProfileCreate,
    db: Session = Depends(get_db)
):
    """Create a profile - users can create for themselves, admins/_user_manager can create for anyone"""
    # Default to current user if no user_id provided (will be enforced by ProfileCreate requiring user_id)
    target_user_id = data.user_id

    # Check if user is trying to create for someone else
    if str(target_user_id) != str(permissions.user_id):
        if not _has_profile_permission(permissions):
            raise ForbiddenException(detail="Cannot create profile for another user")

    # Check if profile already exists for this user
    existing = db.query(Profile).filter(Profile.user_id == target_user_id).first()
    if existing:
        raise BadRequestException(detail="Profile already exists for this user")

    try:
        profile = Profile(**data.model_dump())
        db.add(profile)
        db.commit()
        db.refresh(profile)
        return ProfileGet.model_validate(profile, from_attributes=True)
    except Exception as e:
        db.rollback()
        raise BadRequestException(detail=str(e))


@profile_router.patch("/{id}", response_model=ProfileGet)
async def update_profile(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    id: UUID | str,
    data: ProfileUpdate,
    db: Session = Depends(get_db)
):
    """Update a profile - users can only update their own, admins/_user_manager can update any"""
    profile = db.query(Profile).filter(Profile.id == id).first()

    if not profile:
        raise NotFoundException(detail="Profile not found")

    if not _can_access_profile(permissions, profile):
        raise NotFoundException(detail="Profile not found")

    try:
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(profile, key, value)

        db.commit()
        db.refresh(profile)
        return ProfileGet.model_validate(profile, from_attributes=True)
    except Exception as e:
        db.rollback()
        raise BadRequestException(detail=str(e))


@profile_router.delete("/{id}", status_code=204)
async def delete_profile(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    id: UUID | str,
    db: Session = Depends(get_db)
):
    """Delete a profile - users can only delete their own, admins/_user_manager can delete any"""
    profile = db.query(Profile).filter(Profile.id == id).first()

    if not profile:
        raise NotFoundException(detail="Profile not found")

    if not _can_access_profile(permissions, profile):
        raise NotFoundException(detail="Profile not found")

    try:
        db.delete(profile)
        db.commit()
    except Exception as e:
        db.rollback()
        raise BadRequestException(detail=str(e))