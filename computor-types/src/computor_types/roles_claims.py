from pydantic import BaseModel, ConfigDict
from typing import Optional


    
from computor_types.base import EntityInterface, ListQuery

class RoleClaimGet(BaseModel):
    role_id: str
    claim_type: str
    claim_value: str
    properties: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)

class RoleClaimList(BaseModel):
    role_id: str
    claim_type: str
    claim_value: str

    model_config = ConfigDict(from_attributes=True)
    
class RoleClaimQuery(ListQuery):
    role_id: Optional[str] = None
    claim_type: Optional[str] = None
    claim_value: Optional[str] = None


class RoleClaimInterface(EntityInterface):
    create = None
    get = RoleClaimGet
    list = RoleClaimList
    update = None
    query = RoleClaimQuery
