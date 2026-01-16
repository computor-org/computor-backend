from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional

from computor_types.base import EntityInterface, ListQuery

# Removed: Ltree (was only used in backend search function)
# Removed: TYPE_CHECKING/Session (was only used in backend search function)

class CourseTutorRepository(BaseModel):
    provider_url: Optional[str] = None
    full_path_assignments: Optional[str] = None
    full_path_student_template: Optional[str] = None

class CourseTutorGet(BaseModel):
    id: str
    title: Optional[str] = None
    course_family_id: Optional[str] = None
    organization_id: Optional[str] = None
    path: str

    repository: CourseTutorRepository

    model_config = ConfigDict(from_attributes=True)

    @field_validator('path', mode='before')
    @classmethod
    def cast_str_to_ltree(cls, value):
        return str(value)

class CourseTutorList(BaseModel):
    id: str
    title: Optional[str] = None
    course_family_id: Optional[str] = None
    organization_id: Optional[str] = None
    path: str

    repository: CourseTutorRepository

    model_config = ConfigDict(from_attributes=True)

    @field_validator('path', mode='before')
    @classmethod
    def cast_str_to_ltree(cls, value):
        return str(value)

class CourseTutorQuery(ListQuery):
    id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    path: Optional[str] = None
    course_family_id: Optional[str] = None
    organization_id: Optional[str] = None

# BACKEND FUNCTION - Moved to backend in Phase 4
# def course_tutor_search(db: 'Session', query, params: Optional[CourseTutorQuery]):
#     """Search function using SQLAlchemy models - belongs in backend."""
#     ...

class CourseTutorInterface(EntityInterface):
    list = CourseTutorList
    query = CourseTutorQuery

    # Note: This is a VIEW endpoint (read-only), not standard CRUD
    # Mounted at /tutors/courses in backend
    # Only supports GET list and GET by id operations