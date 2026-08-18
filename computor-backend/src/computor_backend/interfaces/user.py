"""Backend User interface with SQLAlchemy model."""

from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Query, Session

from computor_types.users import (
    UserInterface as UserInterfaceBase,
    UserQuery,
)
from computor_backend.exceptions import ForbiddenException
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.auth import User
from computor_backend.permissions.core import check_permissions
from computor_backend.permissions.principal import Principal


# Fields a user may change on their *own* record. ``email`` is deliberately
# absent: it is the join key between the Computor user, the Keycloak identity
# and the git-server handle, so a self-service rewrite would orphan the account
# on the next SSO login. ``properties`` carries provisioning state and is not
# the user's to edit either. Both remain writable by admins/_user_manager.
SELF_EDITABLE_USER_FIELDS = frozenset({"given_name", "family_name"})


def custom_permissions_user(
    permissions: Principal,
    db: Session,
    id: UUID,
    entity: Any,
) -> Query:
    """Permission check for user updates, with a self-service carve-out.

    Admins and ``_user_manager`` keep the generic behaviour (the handler
    already excludes service accounts and admins from their reach). Everyone
    else may edit only their own row, and only the display-name fields — the
    query returned by the handler is scoped to the principal, so a patch aimed
    at another user resolves to NotFound.
    """
    query = check_permissions(permissions, User, "update", db)

    if permissions.is_admin or permissions.permitted("user", "update"):
        return query

    if isinstance(entity, BaseModel):
        fields = set(entity.model_dump(exclude_unset=True))
    else:
        fields = set(entity or {})

    forbidden = sorted(fields - SELF_EDITABLE_USER_FIELDS)
    if forbidden:
        raise ForbiddenException(
            detail=(
                "You can only change your own name here; "
                f"{', '.join(forbidden)} is managed for you."
            ),
            context={"fields": forbidden},
        )

    return query


class UserInterface(UserInterfaceBase, BackendEntityInterface):
    """Backend-specific User interface with model and API configuration."""

    model = User
    endpoint = "users"
    cache_ttl = 300  # 5 minutes cache for user data
    custom_permissions = custom_permissions_user

    @staticmethod
    def search(db: Session, query, params: Optional[UserQuery]):
        """
        Apply search filters to user query.

        Args:
            db: Database session
            query: SQLAlchemy query object
            params: User query parameters

        Returns:
            Filtered query object
        """
        if params is None:
            return query

        if params.id is not None:
            query = query.filter(User.id == params.id)
        if params.given_name is not None:
            query = query.filter(User.given_name == params.given_name)
        if params.family_name is not None:
            query = query.filter(User.family_name == params.family_name)
        if params.email is not None:
            query = query.filter(User.email == params.email)
        if params.is_service is not None:
            query = query.filter(User.is_service == params.is_service)
        if params.banned is not None:
            if params.banned:
                query = query.filter(User.banned_at.isnot(None))
            else:
                query = query.filter(User.banned_at.is_(None))
        if params.search:
            # Free-text substring match across name + email, mirroring the
            # ``search`` convention in ``list_mentionable_users``. Runs on top
            # of the permission-scoped query, so it only narrows visibility.
            like = f"%{params.search.strip()}%"
            query = query.filter(
                or_(
                    User.given_name.ilike(like),
                    User.family_name.ilike(like),
                    User.email.ilike(like),
                )
            )

        if params.archived is not None and params.archived:
            query = query.filter(User.archived_at.isnot(None))
        else:
            query = query.filter(User.archived_at.is_(None))

        return query
