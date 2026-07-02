"""Backend User interface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session

from computor_types.users import (
    UserInterface as UserInterfaceBase,
    UserQuery,
)
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.auth import User


class UserInterface(UserInterfaceBase, BackendEntityInterface):
    """Backend-specific User interface with model and API configuration."""

    model = User
    endpoint = "users"
    cache_ttl = 300  # 5 minutes cache for user data

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
