from abc import ABC
from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict

class ListQuery(BaseModel):
    skip: Optional[int] = 0
    limit: Optional[int] = 100

# ACTIONS constant - used by backend for permission generation
ACTIONS = {
    "create":  "create",
    "get":     "get",
    "list":    "list",
    "update":  "update",
}

class EntityInterface(ABC):
    """
    Pure DTO interface - defines data structure only.

    Contains references to Pydantic models for CRUD operations.
    Backend-specific concerns (model, endpoint, caching, search) are handled
    by BackendEntityInterface in computor_backend.interfaces.base.
    """
    create: BaseModel = None
    get: BaseModel = None
    list: BaseModel = None
    update: BaseModel = None
    query: BaseModel = None
    
class BaseEntityList(BaseModel):
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Update timestamp")
    
    # Allow sandboxed datetime types in Temporal workflow sandbox
    model_config = ConfigDict(arbitrary_types_allowed=True)

class BaseEntityGet(BaseEntityList):
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
