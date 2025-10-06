"""Backend User interface with SQLAlchemy model."""

from typing import Optional
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
        if params.id is not None:
            query = query.filter(User.id == params.id)
        if params.given_name is not None:
            query = query.filter(User.given_name == params.given_name)
        if params.family_name is not None:
            query = query.filter(User.family_name == params.family_name)
        if params.email is not None:
            query = query.filter(User.email == params.email)
        if params.number is not None:
            query = query.filter(User.number == params.number)
        if params.user_type is not None:
            query = query.filter(User.user_type == params.user_type)
        if params.username is not None:
            query = query.filter(User.username == params.username)

        if params.archived is not None and params.archived:
            query = query.filter(User.archived_at.isnot(None))
        else:
            query = query.filter(User.archived_at.is_(None))

        return query
