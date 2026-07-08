"""Scoped-entity permission handlers (organization / course_family).

Split out of the former ``handlers_impl`` god-module (TASK-109). Holds:

* ``_ScopedEntityPermissionHandler`` — the shared base that
  ``OrganizationPermissionHandler`` and ``CourseFamilyPermissionHandler``
  now subclass. The two were previously near-verbatim clones differing
  only in scope name, the ``Course`` FK column they cascade read access
  through, and their action→role map.
* ``_ScopeMemberPermissionHandler`` + ``Organization``/``CourseFamily``
  member handlers, and the ``make_scope_member_custom_permissions``
  factory used by the member CRUD interfaces.

``handlers_impl`` re-exports every name below so existing imports keep
working unchanged.
"""

from typing import Optional
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, Query
from computor_backend.permissions.handlers import PermissionHandler
from computor_backend.permissions.query_builders import CoursePermissionQueryBuilder
from computor_backend.permissions.principal import Principal
from computor_backend.exceptions import ForbiddenException
from computor_backend.model.course import Course

__all__ = [
    "_ScopedEntityPermissionHandler",
    "OrganizationPermissionHandler",
    "CourseFamilyPermissionHandler",
    "_ScopeMemberPermissionHandler",
    "OrganizationMemberPermissionHandler",
    "CourseFamilyMemberPermissionHandler",
    "make_scope_member_custom_permissions",
]


class _ScopedEntityPermissionHandler(PermissionHandler):
    """Shared logic for the Organization / CourseFamily entity handlers.

    ``OrganizationPermissionHandler`` and ``CourseFamilyPermissionHandler``
    are identical except for three things, set by the subclass:

    * ``SCOPE`` — the claim namespace / scoped-role scope, e.g.
      ``"organization"`` / ``"course_family"``.
    * ``COURSE_FK`` — the *name* of the ``Course`` column this scope
      cascades read visibility through, e.g. ``"organization_id"`` /
      ``"course_family_id"``. Resolved via ``getattr(Course, ...)`` at
      call time; storing the ``InstrumentedAttribute`` directly on the
      class would trigger its descriptor when read off ``self``.
    * ``ACTION_ROLE_MAP`` — write action → minimum scoped role.

    Read visibility is *additive*: a principal sees a scope entity if
    any of these is true (admin / general permission shortcut aside) —

    - they are a member of any course inside the scope (course role
      cascade UP for read only); or
    - they hold any scoped role on the scope itself.

    Write actions (``update`` / ``archive`` / ``delete``) require an
    explicit scoped role on the scope itself (or admin / general
    permission). Scoped roles do NOT cascade between scopes — being an
    organization ``_owner`` grants no course_family / course privilege.
    """

    # Subclass-provided parameters.
    SCOPE: str = ""
    COURSE_FK: str = ""
    ACTION_ROLE_MAP: dict = {}

    # Course-membership cascade only powers the read filter. Identical for
    # both scopes today; kept as an attribute so subclasses may override.
    READ_COURSE_ROLE = "_student"

    def can_perform_action(
        self,
        principal: Principal,
        action: str,
        resource_id: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> bool:
        if self.check_admin(principal):
            return True

        if self.check_general_permission(principal, action):
            return True

        if action in ("get", "list"):
            return True  # build_query applies the actual filter

        min_role = self.ACTION_ROLE_MAP.get(action)
        if min_role and resource_id:
            return principal.has_scope_role(self.SCOPE, resource_id, min_role)

        return False

    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        if self.check_admin(principal):
            return db.query(self.entity)

        if self.check_general_permission(principal, action):
            return db.query(self.entity)

        if action in ("get", "list"):
            course_fk = getattr(Course, self.COURSE_FK)
            # Visible if course-cascade OR scope_member: union of two id sets.
            course_subquery = (
                CoursePermissionQueryBuilder.user_courses_subquery(
                    principal.user_id, self.READ_COURSE_ROLE, db
                )
            )
            scope_via_course = (
                db.query(course_fk)
                .filter(Course.id.in_(course_subquery))
            )

            scope_via_member_ids = principal.get_scoped_ids_with_role(
                self.SCOPE, "_developer"
            )
            # _developer is the lowest scoped role; hierarchy includes
            # _manager and _owner.

            return db.query(self.entity).filter(
                or_(
                    self.entity.id.in_(scope_via_course),
                    self.entity.id.in_(scope_via_member_ids)
                    if scope_via_member_ids
                    else False,
                )
            )

        min_role = self.ACTION_ROLE_MAP.get(action)
        if min_role:
            scope_ids = principal.get_scoped_ids_with_role(self.SCOPE, min_role)
            if not scope_ids:
                # Empty filter → empty result, not a 403.
                return db.query(self.entity).filter(self.entity.id.in_([]))
            return db.query(self.entity).filter(self.entity.id.in_(scope_ids))

        raise ForbiddenException(detail={"entity": self.resource_name})


class OrganizationPermissionHandler(_ScopedEntityPermissionHandler):
    """Permission handler for Organization entity.

    See ``_ScopedEntityPermissionHandler`` for the (scope-parametrized)
    read/write model. Read visibility is additive (course-membership
    cascade UP, plus explicit scoped role on the org); write actions
    (``update`` / ``archive`` / ``delete``) need an explicit scoped role
    on the org itself. Scoped roles do NOT cascade between scopes.
    """

    SCOPE = "organization"
    COURSE_FK = "organization_id"

    # update / archive / delete: developer can edit, owner-only deletes.
    ACTION_ROLE_MAP = {
        "update": "_developer",
        "archive": "_owner",
        "delete": "_owner",
    }


class CourseFamilyPermissionHandler(_ScopedEntityPermissionHandler):
    """Permission handler for CourseFamily entity.

    Symmetric to ``OrganizationPermissionHandler``; differs only in the
    scope name and the ``Course`` FK column it cascades through.
    """

    SCOPE = "course_family"
    COURSE_FK = "course_family_id"

    ACTION_ROLE_MAP = {
        "update": "_developer",
        "archive": "_owner",
        "delete": "_owner",
    }


class _ScopeMemberPermissionHandler(PermissionHandler):
    """Shared logic for OrganizationMember / CourseFamilyMember handlers.

    Subclasses set:

    * ``SCOPE``  — the claim namespace, e.g. ``"organization"`` /
      ``"course_family"``;
    * ``SCOPE_FK`` — column on the entity pointing to the parent scope,
      e.g. ``"organization_id"``;
    * ``ROLE_FK`` — column on the entity holding the assigned role,
      e.g. ``"organization_role_id"``.

    Permission model:

    * ``_developer``  → read scope only; cannot read/write members.
    * ``_manager``    → read all members of the scope; create / update /
                        delete members whose role is **not** ``_owner``.
                        A manager cannot grant or revoke ``_owner``.
    * ``_owner``      → full CRUD on members, including ``_owner`` rows.

    A user always sees their own membership row regardless of role.

    The ``UPDATE`` path uses a ``custom_permissions`` callable
    (``make_scope_member_custom_permissions`` below) to additionally
    inspect the new-role payload — this prevents a manager from
    promoting an existing membership to ``_owner`` via PATCH, which
    the row-level filter alone would not catch. ``DELETE`` does not
    need the extra hook because ``build_query`` already excludes
    ``_owner`` rows from a manager's deletable set.
    """

    SCOPE: str = ""
    SCOPE_FK: str = ""
    ROLE_FK: str = ""

    def can_perform_action(
        self,
        principal: Principal,
        action: str,
        resource_id: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> bool:
        if self.check_admin(principal):
            return True
        if self.check_general_permission(principal, action):
            return True

        if action == "create":
            ctx = context or {}
            scope_id = ctx.get(self.SCOPE_FK)
            target_role = ctx.get(self.ROLE_FK)
            if not scope_id or not target_role:
                return False
            scope_id = str(scope_id)
            # Owner can assign any role.
            if principal.has_scope_role(self.SCOPE, scope_id, "_owner"):
                return True
            # Manager can assign anything except _owner.
            if (
                principal.has_scope_role(self.SCOPE, scope_id, "_manager")
                and target_role != "_owner"
            ):
                return True
            return False

        if action in ("update", "delete") and resource_id:
            # build_query applies the row-level restriction.
            return True

        if action in ("list", "get"):
            return True

        return False

    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        scope_fk = getattr(self.entity, self.SCOPE_FK)
        role_fk = getattr(self.entity, self.ROLE_FK)

        if self.check_admin(principal):
            return db.query(self.entity)
        if self.check_general_permission(principal, action):
            return db.query(self.entity)

        owner_scopes = principal.get_scoped_ids_with_role(self.SCOPE, "_owner")
        manager_scopes = principal.get_scoped_ids_with_role(self.SCOPE, "_manager")
        # Restrict manager-only set to scopes where principal is NOT owner,
        # so each filter clause stays well-defined.
        manager_only_scopes = manager_scopes - owner_scopes

        if action in ("update", "delete"):
            clauses = []
            if owner_scopes:
                # Owners can edit any row in their scopes.
                clauses.append(scope_fk.in_(owner_scopes))
            if manager_only_scopes:
                # Managers can edit non-_owner rows only.
                clauses.append(
                    and_(
                        scope_fk.in_(manager_only_scopes),
                        role_fk != "_owner",
                    )
                )
            if not clauses:
                return db.query(self.entity).filter(self.entity.id.in_([]))
            return db.query(self.entity).filter(or_(*clauses))

        if action in ("list", "get"):
            # Members of the scope visible to anyone with at least
            # _manager (they need to see the roster). Plus the user's
            # own membership row.
            visible_scopes = owner_scopes | manager_only_scopes
            user_filter = self.entity.user_id == principal.user_id
            if visible_scopes:
                return db.query(self.entity).filter(
                    or_(scope_fk.in_(visible_scopes), user_filter)
                )
            return db.query(self.entity).filter(user_filter)

        raise ForbiddenException(detail={"entity": self.resource_name})


class OrganizationMemberPermissionHandler(_ScopeMemberPermissionHandler):
    SCOPE = "organization"
    SCOPE_FK = "organization_id"
    ROLE_FK = "organization_role_id"


class CourseFamilyMemberPermissionHandler(_ScopeMemberPermissionHandler):
    SCOPE = "course_family"
    SCOPE_FK = "course_family_id"
    ROLE_FK = "course_family_role_id"


def make_scope_member_custom_permissions(
    model: type, scope: str, scope_fk: str, role_fk: str
):
    """Return a ``custom_permissions`` callable for a scoped member entity.

    The build_query filter already restricts which rows a principal can
    delete (a ``_manager`` cannot see ``_owner`` rows), but UPDATE goes
    through ``custom_permissions`` and the row-level filter alone does
    not inspect the *new* role being assigned. This callable closes
    that gap by examining the request payload:

    * Reject the update if the row does not exist (NotFound -> empty).
    * Require the principal to have at least ``_manager`` on the scope.
    * Reject if the row is currently ``_owner`` and the principal is
      not ``_owner`` (a manager cannot demote an owner).
    * Reject if the payload tries to set the role to ``_owner`` and the
      principal is not ``_owner`` (a manager cannot promote to owner).

    Returns a passthrough query that the CRUD layer narrows to ``id``.
    """

    def custom_permissions(
        principal: Principal,
        db: Session,
        id,
        entity,
    ) -> Query:
        if principal.is_admin:
            return db.query(model)

        row = db.query(model).filter(model.id == id).first()
        if row is None:
            return db.query(model).filter(model.id == id)

        scope_id = str(getattr(row, scope_fk))
        current_role = getattr(row, role_fk)

        if not principal.has_scope_role(scope, scope_id, "_manager"):
            raise ForbiddenException(
                detail=(
                    f"You need at least _manager on this {scope} to modify "
                    "its memberships"
                )
            )

        is_scope_owner = principal.has_scope_role(scope, scope_id, "_owner")

        if current_role == "_owner" and not is_scope_owner:
            raise ForbiddenException(
                error_code="AUTHZ_005",
                detail="Only an _owner of this scope can modify an _owner membership",
                context={"scope": scope, "scope_id": scope_id, "current_role": current_role},
            )

        new_role = getattr(entity, role_fk, None)
        if new_role is not None and new_role == "_owner" and not is_scope_owner:
            raise ForbiddenException(
                error_code="AUTHZ_005",
                detail="Only an _owner of this scope can grant the _owner role",
                context={"scope": scope, "scope_id": scope_id, "target_role": new_role},
            )

        return db.query(model)

    return custom_permissions
