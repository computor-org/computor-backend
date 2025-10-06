from abc import ABC
from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict

class ListQuery(BaseModel):
    skip: Optional[int] = 0
    limit: Optional[int] = 100

ACTIONS = {
    "create":  "create",
    "get":     "get",
    "list":    "list",
    "update":  "update",
}
    
class EntityInterface(ABC):
    create: BaseModel = None
    get: BaseModel = None
    list: BaseModel = None
    update: BaseModel = None
    query: BaseModel = None
    search: Any = None
    endpoint: str = None
    model: Any = None

    cache_ttl: int = 15

    post_create: Any = None
    post_update: Any = None

    def claim_values(self) -> List[tuple[str,str]]:
        model = self.model
        claims = []
        for attr, action in ACTIONS.items():
            if hasattr(self, attr):
                # Normalize to plural form to match new permission system
                claims.append(("permissions", f"{model.__tablename__}:{action}"))
        return claims
    
class BaseEntityList(BaseModel):
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Update timestamp")
    
    # Allow sandboxed datetime types in Temporal workflow sandbox
    model_config = ConfigDict(arbitrary_types_allowed=True)

class BaseEntityGet(BaseEntityList):
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
