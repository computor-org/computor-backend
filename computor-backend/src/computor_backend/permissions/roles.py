"""Canonical role identifiers and derived role-list helpers.

Single source of truth for the string values stored in
``CourseMember.course_role_id``, ``OrganizationMember.role_id``, and
``CourseFamilyMember.role_id``. Prefer ``CourseRole.LECTURER`` over the
raw string ``"_lecturer"`` and ``LECTURER_AND_ABOVE`` over the
hand-rolled list ``["_lecturer", "_maintainer", "_owner"]``.

The role-list constants are derived from the hierarchies defined in
``principal.py`` so they cannot drift from the hierarchy itself.
``CourseRole``/``ScopeRole`` are ``str`` subclasses, so enum members
compare equal to their underlying string and work directly in
SQLAlchemy filters and ``.in_(...)`` clauses.
"""
from enum import Enum
from typing import Tuple

from computor_backend.permissions.principal import (
    course_role_hierarchy,
    organization_role_hierarchy,
)


class CourseRole(str, Enum):
    """Course role identifiers (values stored in ``course_role_id``)."""
    OWNER = "_owner"
    MAINTAINER = "_maintainer"
    LECTURER = "_lecturer"
    TUTOR = "_tutor"
    STUDENT = "_student"


class ScopeRole(str, Enum):
    """Organization / course-family role identifiers.

    The same three-level ladder powers both organization and
    course-family memberships — ``organization_role_hierarchy`` and
    ``course_family_role_hierarchy`` share their level table.
    """
    OWNER = "_owner"
    MANAGER = "_manager"
    DEVELOPER = "_developer"


class SystemRole(str, Enum):
    """System-wide role identifiers (``UserRole.role_id``)."""
    ADMIN = "_admin"


def _course_roles_at_or_above(role: CourseRole) -> Tuple[str, ...]:
    return tuple(course_role_hierarchy.get_allowed_roles(role.value))


def _scope_roles_at_or_above(role: ScopeRole) -> Tuple[str, ...]:
    return tuple(organization_role_hierarchy.get_allowed_roles(role.value))


# Course-role lists, derived from the hierarchy. Use these in
# ``CourseMember.course_role_id.in_(...)`` filters.
OWNER_ONLY: Tuple[str, ...] = _course_roles_at_or_above(CourseRole.OWNER)
MAINTAINER_AND_ABOVE: Tuple[str, ...] = _course_roles_at_or_above(CourseRole.MAINTAINER)
LECTURER_AND_ABOVE: Tuple[str, ...] = _course_roles_at_or_above(CourseRole.LECTURER)
TUTOR_AND_ABOVE: Tuple[str, ...] = _course_roles_at_or_above(CourseRole.TUTOR)

# Organization / course-family scope-role lists. Same three-level ladder
# applies to both, so a single constant set suffices.
SCOPE_OWNER_ONLY: Tuple[str, ...] = _scope_roles_at_or_above(ScopeRole.OWNER)
SCOPE_MANAGER_AND_ABOVE: Tuple[str, ...] = _scope_roles_at_or_above(ScopeRole.MANAGER)
SCOPE_DEVELOPER_AND_ABOVE: Tuple[str, ...] = _scope_roles_at_or_above(ScopeRole.DEVELOPER)
