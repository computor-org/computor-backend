"""User-domain permission handlers.

Split out of the former ``handlers_impl`` god-module (TASK-109). Covers
the identity entities: ``User``, ``Account``, ``Profile`` and
``StudentProfile``. ``handlers_impl`` re-exports every public name here
so existing imports keep working.
"""

from typing import Optional
from sqlalchemy import and_, exists, not_
from sqlalchemy.orm import Session, Query
from computor_backend.permissions.handlers import PermissionHandler
from computor_backend.permissions.query_builders import UserPermissionQueryBuilder
from computor_backend.permissions.principal import Principal
from computor_backend.exceptions import ForbiddenException
from computor_backend.model.auth import User
from computor_backend.model.role import UserRole

__all__ = [
    "UserPermissionHandler",
    "AccountPermissionHandler",
    "ProfilePermissionHandler",
    "StudentProfilePermissionHandler",
]


class UserPermissionHandler(PermissionHandler):
    """Permission handler for User entity"""

    ACTION_PERMISSIONS = {
        "list": ["list", "get"],  # Actions that allow listing
        "get": ["get"],
        "create": ["create"],
        "update": ["update"],
        "delete": ["delete"]
    }

    def can_perform_action(self, principal: Principal, action: str, resource_id: Optional[str] = None, context: Optional[dict] = None) -> bool:
        # Admin can do anything
        if self.check_admin(principal):
            return True

        # Check general permission (e.g., _user_manager)
        if self.check_general_permission(principal, action):
            # User managers can list/get any user
            if action in ["list", "get", "create"]:
                return True

            # For update/delete, user managers cannot modify admins or service accounts.
            # The actual check is in build_query; here we just allow the action through.
            if action in ["update", "delete"] and resource_id:
                return True

        # Users can view themselves
        if action in ["list", "get"] and resource_id == principal.user_id:
            return True

        return False

    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        # Admin gets everything
        if self.check_admin(principal):
            return db.query(self.entity)

        # Check general permission (e.g., _user_manager)
        if self.check_general_permission(principal, action):
            base_query = db.query(self.entity)

            # For update/delete actions, user managers cannot modify admins or service accounts
            if action in ["update", "delete"]:
                # Exclude service accounts
                base_query = base_query.filter(self.entity.is_service == False)

                # Exclude users with admin role
                admin_subquery = exists().where(
                    and_(
                        UserRole.user_id == self.entity.id,
                        UserRole.role_id == "_admin"
                    )
                )
                base_query = base_query.filter(not_(admin_subquery))

            return base_query

        # For list/get, users can see themselves and users in their courses (as tutor+)
        if action in ["list", "get"]:
            return UserPermissionQueryBuilder.filter_visible_users(principal.user_id, db)

        raise ForbiddenException(detail=f"Insufficient permissions to {action} {self.resource_name}")


class AccountPermissionHandler(PermissionHandler):
    """Permission handler for Account entity"""

    def can_perform_action(self, principal: Principal, action: str, resource_id: Optional[str] = None, context: Optional[dict] = None) -> bool:
        if self.check_admin(principal):
            return True

        if self.check_general_permission(principal, action):
            return True

        # Users can view their own accounts
        if action in ["list", "get"]:
            return True

        return False

    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        if self.check_admin(principal):
            return db.query(self.entity)

        if self.check_general_permission(principal, action):
            return db.query(self.entity)

        # Users can only see their own accounts
        if action in ["list", "get"]:
            return (
                db.query(self.entity)
                .join(User, User.id == self.entity.user_id)
                .filter(User.id == principal.user_id)
            )

        # Users may unlink only their OWN, non-built-in accounts. Built-in
        # identity accounts (SSO / Git server) are excluded, so a delete
        # attempt resolves to NotFound. Admins (handled above) can delete any.
        if action == "delete":
            return (
                db.query(self.entity)
                .filter(
                    self.entity.user_id == principal.user_id,
                    self.entity.builtin.is_(False),
                )
            )

        raise ForbiddenException(detail={"entity": self.resource_name})


class ProfilePermissionHandler(PermissionHandler):
    """Permission handler for Profile entity"""

    def can_perform_action(self, principal: Principal, action: str, resource_id: Optional[str] = None, context: Optional[dict] = None) -> bool:
        if self.check_admin(principal):
            return True

        if self.check_general_permission(principal, action):
            return True

        # Users can create their own profile
        if action == "create":
            if context and context.get("user_id") == principal.user_id:
                return True
            return False

        # Users can view and update their own profile
        if action in ["list", "get", "update"]:
            return True

        return False

    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        if self.check_admin(principal):
            return db.query(self.entity)

        if self.check_general_permission(principal, action):
            return db.query(self.entity)

        if action in ["list", "get", "update"]:
            return db.query(self.entity).filter(self.entity.user_id == principal.user_id)

        raise ForbiddenException(detail={"entity": self.resource_name})


class StudentProfilePermissionHandler(PermissionHandler):
    """Permission handler for StudentProfile entity

    Students are READ-ONLY - they can only view their student profiles.
    Only admins and users with general permissions can create/update/delete.
    """

    def can_perform_action(self, principal: Principal, action: str, resource_id: Optional[str] = None, context: Optional[dict] = None) -> bool:
        if self.check_admin(principal):
            return True

        if self.check_general_permission(principal, action):
            return True

        # Students can ONLY view (list/get) their own student profiles
        # They CANNOT create, update, or delete
        if action in ["list", "get"]:
            return True

        # Block all other actions (create, update, delete) for regular users
        return False

    def build_query(self, principal: Principal, action: str, db: Session) -> Query:
        if self.check_admin(principal):
            return db.query(self.entity)

        if self.check_general_permission(principal, action):
            return db.query(self.entity)

        # Users can only list/get their own student profiles
        if action in ["list", "get"]:
            return db.query(self.entity).filter(self.entity.user_id == principal.user_id)

        raise ForbiddenException(detail={"entity": self.resource_name})
