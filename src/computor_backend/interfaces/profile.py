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
        """
        Apply search filters to profile query.
        
        Note: Implement specific filters based on query parameters.
        This is a placeholder - update with actual filter logic.
        """
        # TODO: Implement search filters based on ProfileQuery fields
        return query
