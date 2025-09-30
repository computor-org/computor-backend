from typing import Annotated
from uuid import UUID
from fastapi import Depends, Response
from fastapi import APIRouter
from sqlalchemy.orm import Session
from sqlalchemy import exc
from ctutor_backend.api.exceptions import InternalServerException

from ctutor_backend.api.crud import create_db, list_db
from ctutor_backend.api.exceptions import NotFoundException
from ctutor_backend.permissions.auth import get_current_principal
from ctutor_backend.permissions.core import check_permissions
from ctutor_backend.permissions.principal import Principal
from ctutor_backend.database import get_db
from ctutor_backend.interface.user_roles import UserRoleCreate, UserRoleGet, UserRoleInterface, UserRoleList, UserRoleQuery
from ctutor_backend.model.role import UserRole
user_roles_router = APIRouter()

@user_roles_router.get("", response_model=list[UserRoleList])
async def list_user_roles(
    permissions: Annotated[Principal, Depends(get_current_principal)],
    response: Response,
    db: Session = Depends(get_db),
    params: UserRoleQuery = Depends()
):
    """List user roles"""
    
    list_result, total = await list_db(permissions, db, params, UserRoleInterface)
    response.headers["X-Total-Count"] = str(total)

    return list_result

@user_roles_router.get("/users/{user_id}/roles/{role_id}", response_model=UserRoleGet)
async def get_user_role(
    permissions: Annotated[Principal, Depends(get_current_principal)], 
    user_id: UUID | str, 
    role_id: UUID | str, 
    db: Session = Depends(get_db)
):
    """Get a specific user role by user_id and role_id"""
    query = check_permissions(permissions, UserRole, "get", db)
    entity = query.filter(UserRole.user_id == user_id, UserRole.role_id == role_id).first()
    
    if not entity:
        raise NotFoundException(detail=f"UserRole not found for user {user_id} and role {role_id}")
    
    return UserRoleGet.model_validate(entity)

@user_roles_router.post("", response_model=UserRoleGet)
async def create_user_role(permissions: Annotated[Principal, Depends(get_current_principal)], entity: UserRoleCreate, db: Session = Depends(get_db)):
    return await create_db(permissions, db, entity, UserRole, UserRoleGet)

@user_roles_router.delete("/users/{user_id}/roles/{role_id}", response_model=list[UserRoleList])
async def delete_user_role(permissions: Annotated[Principal, Depends(get_current_principal)], user_id: UUID | str, role_id: UUID | str, db: Session = Depends(get_db)):

    query = check_permissions(permissions,UserRole,"delete",db)
    
    entity = query.filter(UserRole.user_id == user_id, UserRole.role_id == role_id).first()
    
    if not entity:
        raise NotFoundException(detail=f"{UserRole.__name__} not found")

    try:
        db.delete(entity)
        db.commit()
    except exc.SQLAlchemyError as e:
        # TODO: proper error handling
        raise InternalServerException(detail=e.args)
    except Exception as e:
        raise InternalServerException(detail=e.args)

    return {"ok": True}