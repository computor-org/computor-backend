from typing import Annotated
from uuid import UUID
from fastapi import Depends, Response
from fastapi import APIRouter
from sqlalchemy.orm import Session

from ctutor_backend.business_logic.crud import (
    create_entity as create_db,
    list_entities as list_db
)
from ctutor_backend.permissions.auth import get_current_principal
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.database import get_db
from ctutor_backend.interface.user_roles import (
    UserRoleCreate,
    UserRoleGet,
    UserRoleInterface,
    UserRoleList,
    UserRoleQuery
)
from ctutor_backend.model.role import UserRole

# Import business logic
from ctutor_backend.business_logic.user_roles import (
    get_user_role,
    delete_user_role,
)

user_roles_router = APIRouter()


@user_roles_router.get("", response_model=list[UserRoleList])
async def list_user_roles(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    response: Response,
    db: Session = Depends(get_db),
    params: UserRoleQuery = Depends()
):
    """List user roles."""

    list_result, total = await list_db(permissions, db, params, UserRoleInterface)
    response.headers["X-Total-Count"] = str(total)

    return list_result


@user_roles_router.get("/users/{user_id}/roles/{role_id}", response_model=UserRoleGet)
async def get_user_role_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    user_id: UUID | str,
    role_id: UUID | str,
    db: Session = Depends(get_db)
):
    """Get a specific user role by user_id and role_id."""
    entity = get_user_role(user_id, role_id, permissions, db)
    return UserRoleGet.model_validate(entity)


@user_roles_router.post("", response_model=UserRoleGet)
async def create_user_role(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    entity: UserRoleCreate,
    db: Session = Depends(get_db)
):
    """Create a new user role."""
    return await create_db(permissions, db, entity, UserRole, UserRoleGet)


@user_roles_router.delete("/users/{user_id}/roles/{role_id}", response_model=dict)
async def delete_user_role_endpoint(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    user_id: UUID | str,
    role_id: UUID | str,
    db: Session = Depends(get_db)
):
    """Delete a user role."""
    return delete_user_role(user_id, role_id, permissions, db)
