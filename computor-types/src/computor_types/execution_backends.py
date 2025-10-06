from pydantic import BaseModel, ConfigDict
from typing import Optional


    
from computor_types.base import BaseEntityGet, EntityInterface, ListQuery

class ExecutionBackendCreate(BaseModel):
    type: str
    slug: str
    properties: Optional[dict] = None

class ExecutionBackendGet(BaseEntityGet,ExecutionBackendCreate):
    id: str

    model_config = ConfigDict(from_attributes=True)

class ExecutionBackendList(ExecutionBackendGet,ExecutionBackendCreate):
    model_config = ConfigDict(from_attributes=True)

class ExecutionBackendUpdate(BaseModel):
    type: Optional[str] = None
    slug: Optional[str] = None
    properties: Optional[dict] = None

class ExecutionBackendQuery(ListQuery):
    id: Optional[str] = None
    type: Optional[str] = None
    slug: Optional[str] = None
    properties: Optional[str] = None


class ExecutionBackendInterface(EntityInterface):
    create = ExecutionBackendCreate
    get = ExecutionBackendGet
    list = ExecutionBackendList
    update = ExecutionBackendUpdate
    query = ExecutionBackendQuery
