"""DTOs for CourseFamilyMember — per-course-family role membership.

Mirrors :mod:`computor_types.course_members` but for the course_family
scope. Used to grant explicit write/admin rights on a course_family to
a user.
"""
from typing import Optional

from pydantic import BaseModel, ConfigDict

from computor_types.base import BaseEntityGet, EntityInterface, ListQuery
from computor_types.users import UserList


class CourseFamilyMemberCreate(BaseModel):
    id: Optional[str] = None
    properties: Optional[dict] = None
    user_id: str
    course_family_id: str
    course_family_role_id: str


class CourseFamilyMemberGet(BaseEntityGet):
    id: str
    properties: Optional[dict] = None
    user_id: str
    course_family_id: str
    course_family_role_id: str
    user: Optional[UserList] = None

    model_config = ConfigDict(from_attributes=True)


class CourseFamilyMemberList(BaseModel):
    id: str
    user_id: str
    course_family_id: str
    course_family_role_id: str
    user: Optional[UserList] = None

    model_config = ConfigDict(from_attributes=True)


class CourseFamilyMemberUpdate(BaseModel):
    properties: Optional[dict] = None
    course_family_role_id: Optional[str] = None


class CourseFamilyMemberQuery(ListQuery):
    id: Optional[str] = None
    user_id: Optional[str] = None
    course_family_id: Optional[str] = None
    course_family_role_id: Optional[str] = None


class CourseFamilyMemberInterface(EntityInterface):
    create = CourseFamilyMemberCreate
    get = CourseFamilyMemberGet
    list = CourseFamilyMemberList
    update = CourseFamilyMemberUpdate
    query = CourseFamilyMemberQuery
