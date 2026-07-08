"""Miscellaneous permission handlers.

Split out of the former ``handlers_impl`` god-module (TASK-109). Covers
the handlers that don't belong to the user / course / scoped domains:
``ReadOnlyPermissionHandler`` (lookup tables), ``ExamplePermissionHandler``
(shared example library) and ``UserRolePermissionHandler`` (global
role-assignment junction). ``handlers_impl`` re-exports every public name
here so existing imports keep working.
"""

from typing import Optional
from sqlalchemy.orm import Session, Query
from computor_backend.permissions.handlers import PermissionHandler
from computor_backend.permissions.principal import Principal
from computor_backend.exceptions import ForbiddenException

__all__ = [
    "ReadOnlyPermissionHandler",
    "ExamplePermissionHandler",
    "UserRolePermissionHandler",
]


class ReadOnlyPermissionHandler(PermissionHandler):
    """Permission handler for read-only entities like CourseRole, CourseContentKind"""

    def can_perform_action(
        self,
        principal: Principal,
        action: str,
        resource_id: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> bool:
        # ``context`` is accepted for signature parity with the base
        # ``PermissionHandler.can_perform_action`` and the call site in
        # ``business_logic/crud.py::create_entity`` — read-only entities
        # don't actually consult it. Without this kwarg the create path
        # raised a TypeError for any registered ReadOnly entity.
        if self.check_admin(principal):
            return True

        # Everyone can read these entities
        if action in ["list", "get"]:
            return True

        # Only admin can modify
        return self.check_general_permission(principal, action)

    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        if self.check_admin(principal):
            return db.query(self.entity)

        if action in ["list", "get"]:
            return db.query(self.entity)

        if self.check_general_permission(principal, action):
            return db.query(self.entity)

        raise ForbiddenException(detail={"entity": self.resource_name})


class UserRolePermissionHandler(PermissionHandler):
    """Permission handler for the ``user_role`` junction table.

    Reads are open (every authenticated user can list / get user-role
    assignments). Writes are gated by the standard ``user_role:<action>``
    claim — held by the ``_user_manager`` role today.

    Critical extra rule: even with the claim, non-admins cannot
    create / update / delete a row whose ``role_id`` is ``_admin``.
    Without this, anyone with ``_user_manager`` could grant themselves
    or others the ``_admin`` system role and escalate. Mirrors the
    ``_manager``-can't-promote-to-``_owner`` pattern that landed for
    scoped roles in PR #112.

    The ``context`` dict that ``business_logic/crud.py::create_entity``
    builds from the request payload includes ``role_id`` (any
    ``*_id`` field is folded in), so the create path sees the target
    role before it commits. The ``build_query`` path filters out admin
    rows for non-admins so update / delete URLs that target an admin
    row resolve to ``NotFound`` rather than succeed silently.
    """

    PROTECTED_ROLE_ID = "_admin"

    def can_perform_action(
        self,
        principal: Principal,
        action: str,
        resource_id: Optional[str] = None,
        context: Optional[dict] = None,
    ) -> bool:
        if self.check_admin(principal):
            return True

        if action in ("list", "get"):
            return True

        # Writes require the general claim (typically held by
        # ``_user_manager``).
        if not self.check_general_permission(principal, action):
            return False

        # Even with the claim, only admins may grant ``_admin``.
        if context and context.get("role_id") == self.PROTECTED_ROLE_ID:
            return False

        return True

    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        if self.check_admin(principal):
            return db.query(self.entity)

        if action in ("list", "get"):
            return db.query(self.entity)

        if self.check_general_permission(principal, action):
            # Filter out admin rows so non-admins targeting an
            # admin assignment by (user_id, role_id) get a clean
            # NotFound, not a successful update / delete.
            return db.query(self.entity).filter(
                self.entity.role_id != self.PROTECTED_ROLE_ID
            )

        raise ForbiddenException(detail={"entity": self.resource_name})


class ExamplePermissionHandler(PermissionHandler):
    """Permission handler for Example entities.

    Access rules:
    - Admin: full access.
    - Holder of the general ``<entity>:<action>`` claim: full access for that
      action. Example authoring (create/update/delete) is granted only to
      ``_example_manager`` (see ``claims_example_manager``);
      ``_organization_manager`` holds the read claims (get/list) only.
    - A course ``_lecturer`` and above (in ANY course): READ-ONLY access
      (get/list/download) — lecturers may browse the shared example library
      but not author it.
    - _tutor / _student: no access.
    """

    # Actions a course lecturer may perform on the shared example library.
    # Authoring actions (create/update/delete/upload) are deliberately absent
    # so they fall through to the admin-or-general-claim check and are thus
    # reserved to ``_example_manager`` / admin.
    READ_ACTIONS = frozenset({"get", "list", "download"})

    ACTION_ROLE_MAP = {
        "get": "_lecturer",
        "list": "_lecturer",
        "download": "_lecturer",
    }

    def _lecturer_read_allowed(self, principal: Principal, action: str) -> bool:
        """True if a lecturer-in-any-course may perform this (read-only) action."""
        if action not in self.READ_ACTIONS:
            return False
        min_role = self.ACTION_ROLE_MAP.get(action, "_lecturer")
        return bool(principal.get_courses_with_role(min_role))

    def can_perform_action(self, principal: Principal, action: str, resource_id: Optional[str] = None, context: Optional[dict] = None) -> bool:
        if self.check_admin(principal):
            return True

        # Holder of the general <entity>:<action> claim — _example_manager for
        # authoring, _organization_manager for reads.
        if self.check_general_permission(principal, action):
            return True

        # Lecturers get read-only access to the shared example library.
        return self._lecturer_read_allowed(principal, action)

    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        if self.check_admin(principal):
            return db.query(self.entity)

        if self.check_general_permission(principal, action):
            return db.query(self.entity)

        if self._lecturer_read_allowed(principal, action):
            return db.query(self.entity)

        # No access for students, tutors, or lecturers attempting to author.
        raise ForbiddenException(detail={"entity": self.resource_name, "message": "Examples are only accessible to lecturers and above; authoring is restricted to the _example_manager role"})
