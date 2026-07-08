"""Business logic for user management and authentication."""
import logging
from typing import List, Dict
from uuid import UUID

from sqlalchemy.orm import Session

from computor_backend.exceptions import NotFoundException
from computor_backend.model.auth import User
from computor_backend.model.course import CourseMember
from computor_backend.permissions.principal import Principal
from computor_types.users import UserScopes

logger = logging.getLogger(__name__)

COURSE_ROLE_VIEW_MAP: Dict[str, List[str]] = {
    "_student": ["student"],
    "_tutor": ["student", "tutor"],
}
ELEVATED_COURSE_ROLES = {"_lecturer", "_maintainer", "_owner"}


def get_current_user(user_id: str, db: Session) -> User:
    """Get the current authenticated user."""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise NotFoundException()
        return user
    except Exception as e:
        logger.error(f"Error fetching user: {e}")
        raise NotFoundException() from e


def get_user_scopes_from_principal(principal: Principal) -> UserScopes:
    """Project the registered scope namespaces off ``principal.claims``.

    Pure transformation — claims are already resolved when the principal
    was built, so no DB hit is needed. Only the three currently-registered
    namespaces are surfaced (``organization``, ``course_family``,
    ``course``); other entries in ``claims.dependent`` are ignored.

    For admins, the per-scope maps are returned empty — admins have no
    explicit per-scope claims and the client should treat ``is_admin``
    as a "has every role on every scope" sentinel (matching what the
    server's ``has_scope_role`` does).
    """
    dependent = principal.claims.dependent if principal.claims else {}
    return UserScopes(
        is_admin=bool(getattr(principal, "is_admin", False)),
        organization={
            scope_id: sorted(roles)
            for scope_id, roles in dependent.get("organization", {}).items()
        },
        course_family={
            scope_id: sorted(roles)
            for scope_id, roles in dependent.get("course_family", {}).items()
        },
        course={
            scope_id: sorted(roles)
            for scope_id, roles in dependent.get("course", {}).items()
        },
    )


def get_course_views_for_user(principal: Principal) -> List[str]:
    """Available client views for the current principal.

    Pure projection of the already-resolved principal claims — no DB hit,
    mirroring ``get_user_scopes_from_principal``.

    The ``lecturer`` view is the *org → course-family → course creation
    pipeline* plus the example library, NOT "lecturer of one course". It is
    therefore granted to anyone who can create or manage any of those scopes:

      * global ``_admin`` or ``_organization_manager`` — manage ALL
        organizations, families and courses;
      * global ``_example_manager`` — owns the example library, which lives
        under the same authoring surface in the clients (web "Management"
        section, VS Code lecturer tree);
      * any organization-scoped role (``_owner``/``_manager``/``_developer``);
      * any course-family-scoped role (same three);
      * a course role of ``_lecturer`` or higher.

    A plain lecturer who holds none of the above still gets the view — they
    simply can't create top-level scopes inside it. The view is the same;
    the permissions differ.
    """
    views = set()

    # 1. Global roles. _admin and _organization_manager manage every scope, and
    #    _example_manager owns the example library — all three surface under the
    #    lecturer authoring view in the clients, so without it that surface never
    #    renders (e.g. the VS Code example tree is gated on the lecturer view).
    if (
        principal.is_admin
        or "_organization_manager" in principal.roles
        or "_example_manager" in principal.roles
    ):
        views.add("lecturer")
    if principal.is_admin or "_user_manager" in principal.roles:
        views.add("user_manager")

    dependent = principal.claims.dependent if principal.claims else {}

    # 2. Any organization- or course-family-scoped role means the user can
    #    create/manage courses in that scope → lecturer (pipeline) view.
    if dependent.get("organization") or dependent.get("course_family"):
        views.add("lecturer")

    # 3. Course roles → student / tutor / lecturer (one set of roles per
    #    course; iterate defensively in case a course carries several).
    for course_roles in dependent.get("course", {}).values():
        for role in course_roles:
            role = role.lower()
            if role in COURSE_ROLE_VIEW_MAP:
                views.update(COURSE_ROLE_VIEW_MAP[role])
            elif role in ELEVATED_COURSE_ROLES:
                views.update(["student", "tutor", "lecturer"])

    return sorted(views)


def get_course_views_for_user_by_course(user_id: str, course_id: UUID | str, db: Session) -> List[str]:
    """Get available views based on role for a specific course for the user."""

    # A non-UUID course_id (e.g. a client passing a static route segment like
    # "create" as if it were an id) has no membership. Return [] instead of
    # letting psycopg2 raise "badly formed hexadecimal UUID string" → 500.
    try:
        UUID(str(course_id))
    except (ValueError, TypeError, AttributeError):
        return []

    # Query course membership for the specific course
    course_member = (
        db.query(CourseMember)
        .filter(
            CourseMember.user_id == user_id,
            CourseMember.course_id == course_id
        )
        .first()
    )

    if not course_member or not course_member.course_role_id:
        return []

    role = course_member.course_role_id.lower()
    views = []

    if role in COURSE_ROLE_VIEW_MAP:
        views = COURSE_ROLE_VIEW_MAP[role]
    elif role in ELEVATED_COURSE_ROLES:
        views = ["student", "tutor", "lecturer"]

    return sorted(views)
