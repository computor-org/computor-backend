"""DTOs for OrganizationRole — per-organization role labels.

Mirrors :mod:`computor_types.course_roles`. Built-in roles seeded by
migration ``c8d9e0f1a2b3``: ``_owner``, ``_manager``.
"""
from typing import Optional

from pydantic import BaseModel, ConfigDict

from computor_types.base import EntityInterface, ListQuery


class OrganizationRoleGet(BaseModel):
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    builtin: bool = False

    model_config = ConfigDict(from_attributes=True)


class OrganizationRoleList(OrganizationRoleGet):
    pass


class OrganizationRoleQuery(ListQuery):
    id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    builtin: Optional[bool] = None


class OrganizationRoleInterface(EntityInterface):
    """Read-only role registry — create/update/delete go through migrations."""

    create = None
    get = OrganizationRoleGet
    list = OrganizationRoleList
    update = None
    query = OrganizationRoleQuery
