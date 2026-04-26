"""DTOs for OrganizationMember — per-organization role membership.

Mirrors :mod:`computor_types.course_members` but for the organization
scope. Used to grant explicit write/admin rights on an organization to
a user. Read visibility for organizations is unrelated — it continues
to be derived from course-membership cascade.
"""
from typing import Optional

from pydantic import BaseModel, ConfigDict

from computor_types.base import BaseEntityGet, EntityInterface, ListQuery
from computor_types.users import UserList


class OrganizationMemberCreate(BaseModel):
    id: Optional[str] = None
    properties: Optional[dict] = None
    user_id: str
    organization_id: str
    organization_role_id: str


class OrganizationMemberGet(BaseEntityGet):
    id: str
    properties: Optional[dict] = None
    user_id: str
    organization_id: str
    organization_role_id: str
    user: Optional[UserList] = None

    model_config = ConfigDict(from_attributes=True)


class OrganizationMemberList(BaseModel):
    id: str
    user_id: str
    organization_id: str
    organization_role_id: str
    user: Optional[UserList] = None

    model_config = ConfigDict(from_attributes=True)


class OrganizationMemberUpdate(BaseModel):
    properties: Optional[dict] = None
    organization_role_id: Optional[str] = None


class OrganizationMemberQuery(ListQuery):
    id: Optional[str] = None
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    organization_role_id: Optional[str] = None


class OrganizationMemberInterface(EntityInterface):
    create = OrganizationMemberCreate
    get = OrganizationMemberGet
    list = OrganizationMemberList
    update = OrganizationMemberUpdate
    query = OrganizationMemberQuery
