from pydantic import BaseModel, ConfigDict
from typing import TYPE_CHECKING, Optional, Dict, Any

from computor_types.base import BaseEntityGet, EntityInterface, ListQuery

if TYPE_CHECKING:
        from computor_types.organizations import OrganizationGet

class StudentProfileCreate(BaseModel):
    # id: Optional[str] = None
    student_id: Optional[str] = None
    student_email: Optional[str] = None
    user_id: Optional[str] = None
    organization_id: str

class StudentProfileGet(BaseEntityGet,StudentProfileCreate):
    id: str
    student_id: Optional[str] = None
    student_email: Optional[str] = None
    user_id: str
    organization_id: str

    organization: Optional['OrganizationGet'] = None

    model_config = ConfigDict(from_attributes=True)

class StudentProfileList(BaseModel):
    id: str
    student_id: Optional[str] = None
    student_email: Optional[str] = None
    user_id: str
    organization_id: str

    model_config = ConfigDict(from_attributes=True)

class StudentProfileUpdate(BaseModel):
    student_id: Optional[str] = None
    student_email: Optional[str] = None
    properties: Optional[dict] = None
    organization_id: Optional[str] = None

class StudentProfileQuery(ListQuery):
    id: Optional[str] = None
    student_id: Optional[str] = None
    student_email: Optional[str] = None
    user_id: Optional[str] = None
    organization_id: Optional[str] = None


class StudentProfileInterface(EntityInterface):
    create = StudentProfileCreate
    get = StudentProfileGet
    list = StudentProfileList
    update = StudentProfileUpdate
    query = StudentProfileQuery

# Import OrganizationGet after StudentProfileGet is defined to avoid circular import
from computor_types.organizations import OrganizationGet
# Rebuild the model to resolve forward references
StudentProfileGet.model_rebuild()