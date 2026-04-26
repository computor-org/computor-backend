"""Backend CourseFamilyRoleInterface with SQLAlchemy model."""

from typing import Optional

from sqlalchemy.orm import Session

from computor_types.course_family_roles import (
    CourseFamilyRoleInterface as CourseFamilyRoleInterfaceBase,
    CourseFamilyRoleQuery,
)
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.course import CourseFamilyRole


class CourseFamilyRoleInterface(
    CourseFamilyRoleInterfaceBase, BackendEntityInterface
):
    """Backend-specific CourseFamilyRoleInterface with model and routing."""

    model = CourseFamilyRole
    endpoint = "course-family-roles"
    cache_ttl = 600

    @staticmethod
    def search(db: Session, query, params: Optional[CourseFamilyRoleQuery]):
        if params is None:
            return query
        if params.id is not None:
            query = query.filter(CourseFamilyRole.id == params.id)
        if params.title is not None:
            query = query.filter(CourseFamilyRole.title == params.title)
        if params.builtin is not None:
            query = query.filter(CourseFamilyRole.builtin == params.builtin)
        return query
