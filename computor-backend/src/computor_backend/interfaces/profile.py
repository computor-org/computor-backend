"""Backend Profile interface with SQLAlchemy model."""

from typing import Optional
from sqlalchemy.orm import Session

from computor_types.profiles import (
    ProfileInterface as ProfileInterfaceBase,
    ProfileQuery,
)
from computor_backend.interfaces.base import BackendEntityInterface
from computor_backend.model.auth import Profile


class ProfileInterface(ProfileInterfaceBase, BackendEntityInterface):
    """Backend-specific Profile interface with model attached."""

    model = Profile
    endpoint = "profiles"
    cache_ttl = 300

    @staticmethod
    def search(db: Session, query, params: Optional[ProfileQuery]):
        """Apply search filters to profile query."""
        if params is None:
            return query

        if params.id is not None:
            query = query.filter(Profile.id == params.id)
        if params.nickname is not None:
            query = query.filter(Profile.nickname == params.nickname)
        if params.user_id is not None:
            query = query.filter(Profile.user_id == params.user_id)
        if params.language_code is not None:
            query = query.filter(Profile.language_code == params.language_code)

        return query
