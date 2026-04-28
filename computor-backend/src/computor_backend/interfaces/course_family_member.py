"""Backend CourseFamilyMemberInterface with SQLAlchemy model."""

from typing import Optional

from sqlalchemy.orm import Session

from computor_types.course_family_members import (
    CourseFamilyMemberInterface as CourseFamilyMemberInterfaceBase,
    CourseFamilyMemberQuery,
)
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.course import CourseFamilyMember
from computor_backend.permissions.handlers_impl import (
    make_scope_member_custom_permissions,
)


# See organization_member.py for the rationale: UPDATE must inspect
# the new-role payload to prevent a ``_manager`` from PATCHing an
# existing member to ``_owner`` (privilege escalation that the row-
# level filter alone does not catch).
custom_permissions_course_family_member = make_scope_member_custom_permissions(
    CourseFamilyMember,
    scope="course_family",
    scope_fk="course_family_id",
    role_fk="course_family_role_id",
)


class CourseFamilyMemberInterface(
    CourseFamilyMemberInterfaceBase, BackendEntityInterface
):
    """Backend-specific CourseFamilyMember interface."""

    model = CourseFamilyMember
    endpoint = "course-family-members"
    cache_ttl = 300
    custom_permissions = custom_permissions_course_family_member

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
