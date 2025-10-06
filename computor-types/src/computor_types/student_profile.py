from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any, TYPE_CHECKING

from computor_types.base import BaseEntityGet, EntityInterface, ListQuery

if TYPE_CHECKING:
    from sqlalchemy.orm import Session
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

def student_profile_search(db: 'Session', query, params: Optional[StudentProfileQuery]):
    if params.id != None:
        query = query.filter(id == params.id)
    if params.student_id != None:
        query = query.filter(student_id == params.student_id)
    if params.student_email != None:
        query = query.filter(student_email == params.student_email)
    if params.user_id != None:
        query = query.filter(user_id == params.user_id)
    if params.organization_id != None:
        query = query.filter(organization_id == params.organization_id)
    
    return query

class StudentProfileInterface(EntityInterface):
    create = StudentProfileCreate
    get = StudentProfileGet
    list = StudentProfileList
    update = StudentProfileUpdate
    query = StudentProfileQuery
    search = student_profile_search
    endpoint = "student-profiles"
    model = None  # Set by backend
    cache_ttl = 300  # 5 minutes - student profile changes moderately

# Import OrganizationGet after StudentProfileGet is defined to avoid circular import
from computor_types.organizations import OrganizationGet
# Rebuild the model to resolve forward references
StudentProfileGet.model_rebuild()