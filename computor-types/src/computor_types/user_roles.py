from pydantic import BaseModel, ConfigDict
from typing import Optional


    
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


class UserRoleInterface(EntityInterface):
    create = UserRoleCreate
    get = UserRoleGet
    list = UserRoleList
    update = UserRoleUpdate
    query = UserRoleQuery