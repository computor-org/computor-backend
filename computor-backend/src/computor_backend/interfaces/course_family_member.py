"""Backend CourseFamilyMemberInterface with SQLAlchemy model."""

from typing import Optional

from sqlalchemy.orm import Session

from computor_types.course_family_members import (
    CourseFamilyMemberInterface as CourseFamilyMemberInterfaceBase,
    CourseFamilyMemberQuery,
)
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.course import CourseFamilyMember


class CourseFamilyMemberInterface(
    CourseFamilyMemberInterfaceBase, BackendEntityInterface
):
    """Backend-specific CourseFamilyMember interface."""

    model = CourseFamilyMember
    endpoint = "course-family-members"
    cache_ttl = 300

    @staticmethod
    def search(db: Session, query, params: Optional[CourseFamilyMemberQuery]):
        if params is None:
            return query
        if params.id is not None:
            query = query.filter(CourseFamilyMember.id == params.id)
        if params.user_id is not None:
            query = query.filter(CourseFamilyMember.user_id == params.user_id)
        if params.course_family_id is not None:
            query = query.filter(
                CourseFamilyMember.course_family_id == params.course_family_id
            )
        if params.course_family_role_id is not None:
            query = query.filter(
                CourseFamilyMember.course_family_role_id
                == params.course_family_role_id
            )
        return query
