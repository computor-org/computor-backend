from pydantic import BaseModel, ConfigDict
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

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

def role_claim_search(db: 'Session', query, params: Optional[RoleClaimQuery]):
    if params.role_id != None:
        query = query.filter(role_id == params.role_id)
    if params.claim_type != None:
        query = query.filter(claim_type == params.claim_type)
    if params.claim_value != None:
        query = query.filter(claim_value == params.claim_value)
    return query

class RoleClaimInterface(EntityInterface):
    create = None
    get = RoleClaimGet
    list = RoleClaimList
    update = None
    query = RoleClaimQuery
    search = role_claim_search
    endpoint = "role-claims"
    model = None  # Set by backend
    cache_ttl=600