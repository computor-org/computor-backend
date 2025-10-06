from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from computor_backend.database import get_db
from computor_types.student_profile import (
    StudentProfileGet, StudentProfileList, StudentProfileUpdate,
    StudentProfileCreate, StudentProfileQuery
)
from computor_backend.permissions.auth import get_current_principal
from computor_backend.permissions.principal import Principal

# Import business logic
from computor_backend.business_logic.student_profiles import (
    list_profiles,
    get_profile,
    create_profile,
    update_profile,
    delete_profile,
)

student_profile_router = APIRouter()


@student_profile_router.get("", response_model=list[StudentProfileList])
async def list_student_profiles(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    response: Response,
    params: StudentProfileQuery = Depends(),
    db: Session = Depends(get_db)
):
    """List student profiles - admins/_user_manager see all, users see only their own"""
    profiles, total = list_profiles(permissions, params, db)
    response.headers["X-Total-Count"] = str(total)
    return profiles


@student_profile_router.get("/{id}", response_model=StudentProfileGet)
async def get_student_profile(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    id: UUID | str,
    db: Session = Depends(get_db)
):
    """Get a student profile by ID - users can only get their own, admins/_user_manager can get any"""
    return get_profile(id, permissions, db)


@student_profile_router.post("", response_model=StudentProfileGet, status_code=201)
async def create_student_profile(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    data: StudentProfileCreate,
    db: Session = Depends(get_db)
):
    """Create a student profile - users can create for themselves (user_id optional), admins/_user_manager can create for anyone"""
    return create_profile(data, permissions, db)


@student_profile_router.patch("/{id}", response_model=StudentProfileGet)
async def update_student_profile(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    id: UUID | str,
    data: StudentProfileUpdate,
    db: Session = Depends(get_db)
):
    """Update a student profile - users can only update their own, admins/_user_manager can update any"""
    return update_profile(id, data, permissions, db)


@student_profile_router.delete("/{id}", status_code=204)
async def delete_student_profile(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    id: UUID | str,
    db: Session = Depends(get_db)
):
    """Delete a student profile - users can only delete their own, admins/_user_manager can delete any"""
    delete_profile(id, permissions, db)
