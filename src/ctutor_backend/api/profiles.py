from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from ctutor_backend.database import get_db
from ctutor_backend.interface.profiles import (
    ProfileGet, ProfileList, ProfileUpdate, ProfileCreate,
    ProfileQuery
)
from ctutor_backend.permissions.auth import get_current_principal
from ctutor_backend.permissions.principal import Principal

# Import business logic
from ctutor_backend.business_logic.profiles import (
    list_profiles,
    get_profile,
    create_profile,
    update_profile,
    delete_profile,
)

profile_router = APIRouter()


@profile_router.get("", response_model=list[ProfileList])
async def list_profiles_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    response: Response,
    params: ProfileQuery = Depends(),
    db: Session = Depends(get_db)
):
    """List profiles - admins/_user_manager see all, users see only their own."""

    profiles, total = list_profiles(permissions, params, db)
    response.headers["X-Total-Count"] = str(total)

    return [ProfileList.model_validate(p, from_attributes=True) for p in profiles]


@profile_router.get("/{id}", response_model=ProfileGet)
async def get_profile_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    id: UUID | str,
    db: Session = Depends(get_db)
):
    """Get a profile by ID - users can only get their own, admins/_user_manager can get any."""

    profile = get_profile(id, permissions, db)
    return ProfileGet.model_validate(profile, from_attributes=True)


@profile_router.post("", response_model=ProfileGet, status_code=201)
async def create_profile_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    data: ProfileCreate,
    db: Session = Depends(get_db)
):
    """Create a profile - users can create for themselves, admins/_user_manager can create for anyone."""

    profile = create_profile(data.user_id, data.model_dump(), permissions, db)
    return ProfileGet.model_validate(profile, from_attributes=True)


@profile_router.patch("/{id}", response_model=ProfileGet)
async def update_profile_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    id: UUID | str,
    data: ProfileUpdate,
    db: Session = Depends(get_db)
):
    """Update a profile - users can only update their own, admins/_user_manager can update any."""

    update_data = data.model_dump(exclude_unset=True)
    profile = update_profile(id, update_data, permissions, db)
    return ProfileGet.model_validate(profile, from_attributes=True)


@profile_router.delete("/{id}", status_code=204)
async def delete_profile_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    id: UUID | str,
    db: Session = Depends(get_db)
):
    """Delete a profile - users can only delete their own, admins/_user_manager can delete any."""

    delete_profile(id, permissions, db)
