from pydantic import BaseModel, ConfigDict
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

from computor_types.base import BaseEntityGet, EntityInterface, ListQuery

class UserRoleCreate(BaseModel):
    user_id: str
    role_id: str

class UserRoleGet(BaseEntityGet):
    user_id: str
    role_id: str
    
    model_config = ConfigDict(from_attributes=True)
    
class UserRoleList(BaseModel):
    user_id: str
    role_id: str
    
    model_config = ConfigDict(from_attributes=True)
    
class UserRoleUpdate(BaseModel):
    role_id: str

class UserRoleQuery(ListQuery):
    user_id: Optional[str] = None
    role_id: Optional[str] = None

def user_role_search(db: 'Session', query, params: Optional[UserRoleQuery]):
    if params.user_id != None:
        query = query.filter(user_id == params.user_id)
    if params.role_id != None:
        query = query.filter(role_id == params.role_id)
    return query

class UserRoleInterface(EntityInterface):
    create = UserRoleCreate
    get = UserRoleGet
    list = UserRoleList
    update = UserRoleUpdate
    query = UserRoleQuery
    search = user_role_search
    endpoint = "user-roles"
    model = None  # Set by backend